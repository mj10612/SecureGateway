"""Run with `python examples/multilingual.py`; entirely offline synthetic data."""

from secure_gateway import LocalPrivacyClient
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy
from secure_gateway.session import PrivacySession

SAMPLES = {
    "en": "The synthetic company Willow sends a private file.",
    "ko": "가상 회사 청솔의 비밀 파일입니다.",
    "zh-Hant": "臺北公司的客戶發送秘密文件。",
    "es": "La empresa ficticia Álamo envía datos para Córdoba.",
    "hi": "कंपनी नीलम के लिए गोपनीय फ़ाइल भेजती है।",
    "ar": "شركة نَوْر في القاهرة ترسل مِلفّاً سرياً.",
    "fr": "L’entreprise fictive d’Élodie envoie un fichier à Lyon.",
    "bn": "নীলম কোম্পানি এর জন্য গোপন তথ্য পাঠায়।",
    "pt-BR": "A empresa fictícia Açucena envia dados para Évora.",
    "ru": "Компания Липа отправляет данные для Казани.",
    "ur": "نیلم کمپنی کے لیے خفیہ معلومات بھیجتی ہے۔",
    "id": "Perusahaan Melati mengirim data untuk Bandung.",
    "de-CH": "Die fiktive Firma Weissdorn sendet Daten für Bern.",
    "ja": "東京の会社に顧客情報を送信します。",
    "mr": "कंपनी नीलम साठी गुप्त माहिती पाठवते आहे.",
    "te": "నీలం కంపెనీ కోసం రహస్య సమాచారం ఉంది.",
    "tr": "Şirket İstanbul İÇİN özel dosyayı gönderdi.",
}


def main() -> None:
    for strategy in SurrogateStrategy:
        with LocalPrivacyClient() as client:
            for language, original in SAMPLES.items():
                received = []

                def offline_echo(masked_payload: str) -> str:
                    # A real trusted host would send ONLY this argument.
                    # This example makes no network request.
                    received.append(masked_payload)
                    return masked_payload

                restored = client.request(original, offline_echo,
                                          language=language, strategy=strategy)
                assert len(received) == 1 and received[0] != original
                assert restored.unmasked_text == original

    # Source-language selection is separate from the prose-language tag.
    source = 'privateName=42\nprintf "%s" "$privateName"\n'
    session = PrivacySession("offline-bash")
    engine = MaskingEngine()
    masked = engine.mask_code(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store,
                              language="bash")
    assert "42" in masked.masked_text  # Source numbers are preserved by default.
    assert "privateName" not in masked.masked_text
    assert engine.unmask(masked.masked_text, session.session_id,
                         session.reverse_store, strict=True).unmasked_text == source
    print(f"Verified {len(SAMPLES)} natural languages × 4 strategies and Bash locally.")


if __name__ == "__main__":
    main()
