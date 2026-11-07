"""Behavior contracts for separate quality measurements (#308)."""

import copy
import json

import pytest
from click.testing import CliRunner

from secure_gateway.cli import main


def corpus(*, contextual=False):
    name = 'drift' if contextual else 'KeplerQzx'
    text = f'Review {name}. Do not delete the original.'
    start = text.index(name)
    return {'schema_version': 1, 'corpus_version': 'test-1', 'synthetic': True, 'cases': [{
        'id': 'one', 'template_group': 'one', 'split': 'regression',
        'language': 'en', 'domain': 'general', 'dialect': 'claude',
        'payload': {'model': 'fixture', 'messages': [{'role': 'user', 'content': text}]},
        'echo_path': ['messages', 0, 'content'], 'task_path': ['messages', 0, 'content'],
        'secrets': [{'path': ['messages', 0, 'content'], 'start': start, 'end': start + len(name),
                     'label': 'project', 'fragments': [], 'policy': 'contextual' if contextual else 'explicit',
                     'severity': 'high'}],
        'public': [{'path': ['messages', 0, 'content'], 'start': 0, 'end': 6}],
        'forced_terms': [] if contextual else [name], 'smoke': True,
        'rubric': [{'id': 'intent', 'description': 'Review the project.'},
                   {'id': 'negation', 'description': 'Do not delete the original.'}],
        'human_text': 'Review private_symbol_1. Do not delete the original.'}]}


def test_rejects_bad_annotations_before_executing(tmp_path):
    from secure_gateway.evaluation import load_corpus
    data = corpus()
    data['cases'][0]['secrets'][0]['end'] = 10000
    path = tmp_path / 'corpus.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='span'):
        load_corpus(path)
    data = corpus()
    other = copy.deepcopy(data['cases'][0])
    other.update(id='two', split='holdout')
    data['cases'].append(other)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='template'):
        load_corpus(path)


def test_scores_meaningful_partial_and_repeated_full_exposures():
    from secure_gateway.evaluation import score_field
    source = 'secret_alpha and secret_alpha then Review'
    spans = [{'start': 0, 'end': 12, 'fragments': ['alpha']},
             {'start': 17, 'end': 29, 'fragments': ['alpha']}]
    partial = score_field(source, 'private_symbol_1_alpha and secret_alpha then Review', spans, [])
    assert partial['secrets'][0]['partial_exposure'] is True
    assert partial['secrets'][0]['full_exposure'] is False
    assert partial['secrets'][1]['full_exposure'] is True
    protected = score_field(source, 'private_symbol_1 and private_symbol_1 then Review', spans, [])
    assert all(not x['full_exposure'] and not x['partial_exposure'] for x in protected['secrets'])


def test_privacy_captures_http_restores_and_does_not_measure_llm(tmp_path):
    from secure_gateway.evaluation import run_privacy
    report = run_privacy(corpus(), output_dir=tmp_path / 'result', profile='smoke')
    assert report['metrics']['privacy']['fully_protected'] == 1
    assert report['metrics']['privacy']['accuracy'] == 1.0
    assert report['metrics']['integrity']['roundtrip_passed'] == 1
    assert report['metrics']['integrity']['replay_passed'] == 1
    assert report['metrics']['comprehension']['status'] == 'not_measured'
    assert 'KeplerQzx' not in json.dumps(report['cases'][0]['outbound'])
    assert (tmp_path / 'result' / 'report.json').exists()
    assert (tmp_path / 'result' / 'summary.md').exists()


def test_contextual_labels_are_not_injected_as_protection_policy(tmp_path):
    from secure_gateway.evaluation import run_privacy
    report = run_privacy(corpus(contextual=True), output_dir=tmp_path / 'result', profile='smoke')
    assert report['metrics']['privacy']['full_exposures'] == 1
    assert report['metrics']['privacy']['requests_with_leak'] == 1
    assert report['metrics']['privacy']['accuracy'] == 0.0


def test_unexecuted_requests_are_not_counted_as_safe(tmp_path):
    from secure_gateway.evaluation import run_privacy
    report = run_privacy(corpus(), output_dir=tmp_path / 'result', profile='smoke', max_seconds=0)
    assert report['status'] == 'incomplete'
    assert report['metrics']['privacy']['accuracy'] is None
    assert report['metrics']['privacy']['unmeasured_sensitive'] == 1
    assert report['cases'][0]['status'] == 'budget_exhausted'


def test_compare_rejects_different_corpus_and_finds_new_leaks(tmp_path):
    from secure_gateway.evaluation import compare_reports, run_privacy
    baseline = run_privacy(corpus(), output_dir=tmp_path / 'base', profile='smoke')
    candidate = copy.deepcopy(baseline)
    candidate['cases'][0]['secrets'][0].update(full_exposure=True, partial_exposure=False)
    comparison = compare_reports(baseline, candidate)
    assert comparison['regression'] is True
    assert comparison['new_exposures'] == [{'case_id': 'one', 'occurrence': 0}]
    candidate['metadata']['corpus_hash'] = 'other'
    with pytest.raises(ValueError, match='Incompatible'):
        compare_reports(baseline, candidate)


def test_cli_requires_explicit_real_llm_opt_in(tmp_path):
    result = CliRunner().invoke(main, ['evaluate', '--suite', 'comprehension', '--output-dir', str(tmp_path)])
    assert result.exit_code != 0
    assert '--real-llm' in result.output


def test_packaged_corpus_loads_and_profiles_are_fixed():
    from secure_gateway.evaluation import load_corpus, select_cases
    data = load_corpus()
    assert len(select_cases(data, 'smoke')) == 8
    assert {x['language'] for x in data['cases']} == {'ko', 'en'}
    assert {x['domain'] for x in data['cases']} == {'general', 'defense', 'automotive', 'semiconductor'}


def test_ambiguous_repeated_spelling_cannot_be_certified_protected():
    from secure_gateway.evaluation import score_field
    result = score_field('symbol drift drift', 'private_literal_1 private_literal_1 drift',
                         [{'start': 13, 'end': 18, 'fragments': []}], [{'start': 7, 'end': 12}])
    assert result['secrets'][0]['full_exposure'] is True
    assert result['secrets'][0]['alignment_ambiguous'] is True
    assert result['public'][0]['overmasked'] is True


def test_compare_detects_integrity_regressions_even_without_new_leaks(tmp_path):
    from secure_gateway.evaluation import compare_reports, run_privacy
    baseline = run_privacy(corpus(), output_dir=tmp_path / 'base')
    candidate = copy.deepcopy(baseline)
    candidate['cases'][0]['roundtrip'] = False
    candidate['metrics']['integrity']['snapshot_restart'] = False
    comparison = compare_reports(baseline, candidate)
    assert comparison['regression'] is True
    assert {'case_id': 'one', 'check': 'roundtrip'} in comparison['integrity_regressions']
    assert {'check': 'snapshot_restart'} in comparison['integrity_regressions']


def test_compare_requires_real_compatibility_identifiers():
    from secure_gateway.evaluation import compare_reports
    report = {'schema_version': 1, 'suite': 'privacy', 'metadata': {}, 'cases': [], 'status': 'completed', 'metrics': {}}
    with pytest.raises(ValueError, match='Incompatible'):
        compare_reports(report, report)


def test_tool_json_whitespace_is_reported_separately_from_semantic_restoration(tmp_path):
    from secure_gateway.evaluation import load_corpus, run_privacy
    data = load_corpus()
    data['cases'] = [next(c for c in data['cases'] if c['id'] == 'ko-general-tool-arguments')]
    report = run_privacy(data, output_dir=tmp_path / 'json', profile='release')
    assert report['cases'][0]['roundtrip'] is False
    assert report['cases'][0]['semantic_roundtrip'] is True
    assert report['metrics']['integrity']['semantic_roundtrip_passed'] == 1
    assert '가상별빛보관함' in report['cases'][0]['restored_echo']


def test_engine_alias_provenance_disambiguates_private_and_public_spelling():
    from secure_gateway.evaluation import score_field
    result = score_field('For drift, ordinary drift.', 'For private_symbol_1, ordinary drift.',
                         [{'start': 4, 'end': 9, 'fragments': []}], [{'start': 20, 'end': 25}],
                         aliases={'private_symbol_1': 'drift'})
    assert result['secrets'][0]['full_exposure'] is False
    assert result['secrets'][0]['alignment_ambiguous'] is False
    assert result['public'][0]['overmasked'] is False


def test_unchanged_mapping_is_not_evidence_of_protection():
    from secure_gateway.evaluation import score_field
    result = score_field('drift', 'drift', [{'start': 0, 'end': 5, 'fragments': []}], [], aliases={'drift': 'drift'})
    assert result['secrets'][0]['full_exposure'] is True
