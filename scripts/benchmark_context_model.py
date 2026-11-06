"""Reproduce frozen-encoder context classification with synthetic labelled data.

Install .[context,context-eval] first. Models must be downloaded separately;
this script never uploads texts or downloads model data. Tokenization groups
use twelve rows; encoder inference uses fixed single-context shapes to make
decisions independent of other candidates. --legacy-batching reproduces the
rejected initial variable-shape experiment.
"""
import argparse
import json
from pathlib import Path
import platform
from importlib.metadata import version
import time
from hashlib import sha256

import numpy as np
import onnxruntime as ort
import psutil
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from tokenizers import Tokenizer
from secure_gateway.engine.natural_languages import tokenize
from secure_gateway.engine.tokenizer import MultilingualTokenizer


def lexical_candidate(row):
    """Train on the same complete lexical units used by the gateway."""
    start = row['text'].index(row['candidate'])
    end = start + len(row['candidate'])
    chunks = (MultilingualTokenizer().tokenize(row['text']) if row['language'] in {'en', 'ko'}
              else tokenize(row['text'], row['language']))
    offset = 0
    overlapping = []
    for chunk in chunks:
        right = offset + len(chunk.text)
        if chunk.is_word and offset < end and right > start:
            overlapping.append((offset, right))
        offset = right
    if overlapping:
        start = min(start, overlapping[0][0])
        end = max(end, overlapping[-1][1])
    return {**row, 'label_candidate':row['candidate'], 'candidate':row['text'][start:end]}


class Encoder:
    def __init__(self, folder, prefix, legacy_batching=False):
        started = time.perf_counter()
        self.prefix = prefix
        self.legacy_batching = legacy_batching
        self.tokenizer = Tokenizer.from_file(str(folder / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=128)
        pad = next((token for token in ('<pad>', '[PAD]') if self.tokenizer.token_to_id(token) is not None), None)
        self.tokenizer.enable_padding(length=None if legacy_batching else 128,
                                      pad_id=self.tokenizer.token_to_id(pad), pad_token=pad)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.log_severity_level = 3
        self.session = ort.InferenceSession(str(folder / 'model.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
        self.inputs = {item.name for item in self.session.get_inputs()}
        self.load_seconds = time.perf_counter() - started
        self.timings = []

    def features(self, rows):
        text = [self.prefix + row['text'] for row in rows]
        encoded = self.tokenizer.encode_batch(text)
        feed = {'input_ids': np.array([r.ids for r in encoded], dtype=np.int64), 'attention_mask': np.array([r.attention_mask for r in encoded], dtype=np.int64)}
        if 'token_type_ids' in self.inputs:
            feed['token_type_ids'] = np.array([r.type_ids for r in encoded], dtype=np.int64)
        started = time.perf_counter()
        if self.legacy_batching:
            hidden = self.session.run(None, feed)[0]
        else:
            unique = {}
            for index, value in enumerate(text):
                if value not in unique:
                    unique[value] = self.session.run(None, {key: array[index:index+1] for key, array in feed.items()})[0][0]
            hidden = np.asarray([unique[value] for value in text])
        self.timings.append((time.perf_counter() - started, len(rows), hidden.shape[1]))
        result = []
        for row, encoding, state in zip(rows, encoded, hidden):
            start = len(self.prefix) + row['text'].index(row['candidate'])
            end = start + len(row['candidate'])
            indices = [i for i, (a, b) in enumerate(encoding.offsets) if a < end and b > start]
            if not indices or max(b for a,b in encoding.offsets) < end:
                raise ValueError('Candidate truncated or missing: ' + row['id'])
            target = state[indices].mean(0)
            context = (state * np.asarray(encoding.attention_mask)[:, None]).sum(0) / sum(encoding.attention_mask)
            target = target / max(np.linalg.norm(target), 1e-9)
            context = context / max(np.linalg.norm(context), 1e-9)
            result.append(np.concatenate((target, context, target * context, np.abs(target-context))))
        return np.asarray(result, dtype=np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['minilm', 'e5'], required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--additional-data', type=Path, action='append', default=[])
    parser.add_argument('--models-dir', type=Path, required=True, help='Directory containing minilm/ or e5/ with the pinned upstream files.')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--confidence-floor', type=float, default=0.9)
    parser.add_argument('--raw-spans', action='store_true', help='Reproduce the initial stem-only experiment rather than complete lexical candidates.')
    parser.add_argument('--legacy-batching', action='store_true', help='Reproduce the rejected initial dynamic-batch experiment.')
    args = parser.parse_args()
    if not 0 <= args.confidence_floor <= 1:
        parser.error('Confidence floor must be between zero and one.')
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=True)
    folder = args.models_dir / args.model
    expected = {'minilm':'98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f',
                'e5':'dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88'}
    tokenizer_hash = {'minilm':'2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8',
                      'e5':'0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39'}
    hasher = sha256()
    with (folder / 'model.onnx').open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    if hasher.hexdigest() != expected[args.model]:
        parser.error('Model does not match the pinned experiment weights.')
    if sha256((folder/'tokenizer.json').read_bytes()).hexdigest() != tokenizer_hash[args.model]:
        parser.error('Tokenizer does not match the pinned experiment data.')
    manifest_path = folder/'manifest.json'
    manifest = (json.loads(manifest_path.read_text()) if manifest_path.exists() else
                {'model':args.model,'model_sha256':expected[args.model],
                 'tokenizer_sha256':tokenizer_hash[args.model]})
    data = json.loads(args.data.read_text(encoding='utf-8-sig'))
    rows = data.get('examples', data.get('rows'))
    if rows is None:
        raise ValueError('Missing examples')
    for extra in args.additional_data:
        extra_rows = json.loads(extra.read_text(encoding='utf-8-sig'))['examples']
        if any(row['split']=='test' for row in extra_rows):
            parser.error('Additional training data must not contain test examples.')
        rows.extend(extra_rows)
    if not args.raw_spans:
        rows = [lexical_candidate(row) for row in rows]
    process = psutil.Process()
    before = process.memory_info().rss
    encoder = Encoder(folder, 'query: ' if args.model == 'e5' else '', args.legacy_batching)
    loaded = process.memory_info().rss
    vectors = []
    started = time.perf_counter()
    for start in range(0, len(rows), 12):
        vectors.append(encoder.features(rows[start:start+12]))
    x = np.concatenate(vectors)
    embedding_seconds = time.perf_counter() - started
    y = np.array([r['label'] == 'public' for r in rows], dtype=int)
    train = np.array([r['split'] == 'train' for r in rows])
    cal = np.array([r['split'] in {'calibration', 'cal', 'validation'} for r in rows])
    test = np.array([r['split'] == 'test' for r in rows])
    # Select regularization only on calibration; test never chooses a head/threshold.
    trials = []
    for c in (0.1, 1.0, 10.0):
        head = LogisticRegression(C=c, solver='liblinear', random_state=0, max_iter=1000).fit(x[train], y[train])
        probability = head.predict_proba(x)[:,1]
        threshold = max(args.confidence_floor, min(1.0, float(probability[cal & (y == 0)].max()) + 0.025))
        trials.append((int(((probability >= threshold) & cal & (y == 1)).sum()), c, threshold, head))
    _, chosen_c, threshold, head = max(trials, key=lambda t:(t[0],-t[1]))
    probability = head.predict_proba(x)[:,1]
    recipe = {'lexical_candidates':not args.raw_spans,'onnx_batch_size':12 if args.legacy_batching else 1,'sequence_length':128}
    result = {'model':args.model, 'manifest':manifest, 'platform':platform.platform(),'cpu':platform.processor(),'python':platform.python_version(),'dependencies':{name:version(name) for name in ('onnxruntime','tokenizers','numpy','scikit-learn','psutil')},'encoder_load_seconds':encoder.load_seconds,'rss_load_delta_bytes':loaded-before,'rss_after_embedding_bytes':process.memory_info().rss,'peak_rss_bytes':getattr(process.memory_info(),'peak_wset',process.memory_info().rss),'embedding_seconds':embedding_seconds,'rows':len(rows),'batch_size':12,'onnx_threads':2,'calibrated_threshold':threshold,'regularization_C':chosen_c,'calibration_trials':[{'public_kept':n,'C':c,'threshold':t} for n,c,t,_ in trials],'splits':{},'languages':{},'test_predictions':[]}
    for split, mask in [('train',train),('calibration',cal),('test',test)]:
        kept=probability>=threshold
        result['splits'][split]={'public_total':int((mask & (y==1)).sum()), 'public_kept':int((mask & (y==1) & kept).sum()), 'private_total':int((mask & (y==0)).sum()), 'private_exposed':int((mask & (y==0) & kept).sum()),'auc':float(roc_auc_score(y[mask],probability[mask]))}
    result['feature_recipe'] = recipe
    for language in sorted({r['language'] for r in rows}):
        mask=test & np.array([r['language']==language for r in rows])
        kept=probability>=threshold
        result['languages'][language]={'public_total':int((mask & (y==1)).sum()),'public_kept':int((mask & (y==1) & kept).sum()),'private_total':int((mask & (y==0)).sum()),'private_exposed':int((mask & (y==0) & kept).sum())}
    for row,p,mask in zip(rows,probability,test):
        if mask:
            result['test_predictions'].append({**row,'public_probability':float(p),'public_prediction':bool(p>=threshold)})
    # Single request timings, excluding tokenization from ONNX measurement above.
    single=[]
    controls = [r for language in sorted({r['language'] for r in rows})
                for r in [v for v in rows if v['split']=='test' and v['language']==language][:2]]
    for row in controls:
        at=time.perf_counter()
        encoder.features([row])
        single.append(time.perf_counter()-at)
    result['warm_single_ms']={'median':float(np.median(single)*1000),'p95':float(np.percentile(single,95)*1000)}
    (root/(args.model+'-result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/(args.model+'-head.json')).write_text(json.dumps({'weights':head.coef_[0].tolist(),'intercept':float(head.intercept_[0]),'threshold':threshold}),encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key not in {'test_predictions','languages','manifest'}},indent=2))


if __name__ == '__main__':
    main()
