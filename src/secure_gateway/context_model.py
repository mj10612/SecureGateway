"""Optional offline context-role classifier. Model absence preserves old policy."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path
from threading import RLock

from secure_gateway.context_assets import head_parameters, verify_model, MODEL_ID, PREFIX
from secure_gateway.engine.natural_languages import SUPPORTED_LANGUAGES

# One request can spend at most 64 candidate inferences, across all its fields.
_budget: ContextVar[dict | None] = ContextVar("context_model_budget", default=None)
MAX_CONTEXT_CHARS = 8192


class ContextModel:
    """Optional local context model wrapper with bounded inference and caching."""
    """ContextModel."""
    def __init__(self, directory: Path):
        verify_model(directory)
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        ort.disable_telemetry_events()
        self.np = np
        self.prefix = PREFIX
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=128)
        pad = next(token for token in ("<pad>", "[PAD]") if self.tokenizer.token_to_id(token) is not None)
        self.tokenizer.enable_padding(length=128, pad_id=self.tokenizer.token_to_id(pad), pad_token=pad)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.log_severity_level = 3
        self.session = ort.InferenceSession(str(directory / "model.onnx"), sess_options=options,
                                           providers=["CPUExecutionProvider"])
        self.input_names = {item.name for item in self.session.get_inputs()}
        head = head_parameters()
        self.weights = np.asarray(head["weights"], dtype=np.float32)
        self.intercept = float(head["intercept"])
        self.threshold = float(head["threshold"])
        self.prefix_agreement = head.get("prefix_agreement", True)
        if (self.weights.shape != (1536,) or not np.isfinite(self.weights).all()
                or not np.isfinite(self.intercept) or not 0.9 <= self.threshold <= 1.0
                or type(self.prefix_agreement) is not bool):
            raise ValueError("Invalid context classifier parameters.")
        self.lock = RLock()
        self.calls = self.errors = self.skipped = 0

    @contextmanager
    def request_budget(self):
        """Handle request budget."""
        token = _budget.set({"remaining": 64, "cache": {}})
        try:
            yield
        finally:
            _budget.reset(token)

    def diagnostics(self) -> dict:
        """Return the result of diagnostics.

        Never returns ``None``.
        """
        with self.lock:
            return {"status": "ready", "model": MODEL_ID, "calls": self.calls,
                    "errors": self.errors, "skipped": self.skipped}

    def public_spans(self, text: str, spans: list[tuple[int, int]], language: str) -> frozenset[tuple[int, int]]:
        """Return the result of public spans.

        Never returns ``None``.
        """
        if language not in SUPPORTED_LANGUAGES - {"auto"} or len(text) > MAX_CONTEXT_CHARS or not spans:
            return frozenset()
        with self.lock:
            budget = _budget.get()
            key = (language, sha256(text.encode("utf-8")).digest())
            if budget is not None and key in budget["cache"]:
                return budget["cache"][key].intersection(spans)
            selected = spans[:min(32, budget["remaining"] if budget is not None else 32)]
            self.skipped += len(spans) - len(selected)
            if budget is not None:
                budget["remaining"] -= len(selected)
            if not selected:
                return frozenset()
            try:
                result = self._public_spans(text, selected)
            except Exception:
                # Never retry with plaintext, download a model or log text.
                self.errors += 1
                result = frozenset()
            if budget is not None:
                budget["cache"][key] = result
            return result

    def _public_spans(self, text: str, spans: list[tuple[int, int]]) -> frozenset[tuple[int, int]]:
        np = self.np
        windows = [(0, len(text)) if len(text) <= 256 else
                   (max(0, start - 90), min(len(text), end + 90)) for start, end in spans]
        encoded = self.tokenizer.encode_batch([self.prefix + text[a:b] for a, b in windows])
        feed = {"input_ids": np.asarray([r.ids for r in encoded], dtype=np.int64),
                "attention_mask": np.asarray([r.attention_mask for r in encoded], dtype=np.int64)}
        if "token_type_ids" in self.input_names:
            feed["token_type_ids"] = np.asarray([r.type_ids for r in encoded], dtype=np.int64)
        # Dynamic INT8 quantization can change scores when unrelated batch
        # members change. Score each unique context at fixed shape so replay
        # decisions do not depend on which private tokens were already mapped.
        states = {}
        for index, window in enumerate(windows):
            if window not in states:
                states[window] = self.session.run(None, {key: value[index:index+1] for key, value in feed.items()})[0][0]
                self.calls += 1
        public = set()
        for (start, end), window, row in zip(spans, windows, encoded):
            left, _ = window
            hidden = states[window]
            a, b = start - left + len(self.prefix), end - left + len(self.prefix)
            covered = [(i, lo, hi) for i, (lo, hi) in enumerate(row.offsets) if lo < b and hi > a]
            # Truncation or normalization must not turn a partial word public.
            if not covered or min(lo for _, lo, _ in covered) > a or max(hi for _, _, hi in covered) < b:
                continue
            context = (hidden * np.asarray(row.attention_mask)[:, None]).sum(0) / sum(row.attention_mask)
            context = context / max(float(np.linalg.norm(context)), 1e-9)
            indices = [i for i, _, _ in covered]
            # A grammatical suffix can make a private name's whole-word mean
            # look public. Require agreement from its leading subword evidence
            # as well; disagreement always retains the existing masking.
            groups = [indices]
            if self.prefix_agreement:
                groups.append(indices[:(len(indices) + 1) // 2])
            scores = []
            for group in groups:
                target = hidden[group].mean(0)
                target = target / max(float(np.linalg.norm(target)), 1e-9)
                features = np.concatenate((target, context, target * context, np.abs(target - context)))
                logit = float(features @ self.weights + self.intercept)
                scores.append(1.0 / (1.0 + float(np.exp(-np.clip(logit, -50, 50)))))
            if min(scores) >= self.threshold:
                public.add((start, end))
        return frozenset(public)


def load_context_model(directory) -> tuple[ContextModel | None, str]:
    """Perform load context model.

    Returns ``None``.
    """
    if directory is None:
        return None, "disabled"
    if not isinstance(directory, str) or not directory.strip() or not Path(directory).is_absolute():
        raise ValueError("context_model_path must be an absolute local directory.")
    try:
        return ContextModel(Path(directory)), "ready"
    except ImportError:
        return None, "missing_dependencies"
    except Exception:
        return None, "unavailable"
