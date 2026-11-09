# Issue #324 independent evaluation data

Synthetic corpora for issue #324: two task splits (comprehension under privacy substitution) and two privacy splits (span detection). Every string was newly written for this task, and every person, company, project, email address, phone number and ID is fictional.

## Authorship limits

- Written by one independent worker in a separate worktree. During authoring the worker did **not** open earlier corpora, the old 17 paragraphs, experiment answers or grades, engine or vocabulary implementations, or the coordinator workspace. No task was made by swapping names into an older prompt.
- Labels reflect the author's judgment of each span's role in context. They were not tuned against any engine output, because none was run.
- No LLM inference was used apart from the author writing the corpus. No provider evaluations were run. The coordinator owns execution, with at least 3 fresh repeats per language and arm.
- Emails use `.invalid` domains. Phone numbers use the NANP fictional range `555-01xx` or the Ofcom drama range `07700 900xxx`. IDs carry `SYN`, `VOL`, `TCK` and similar prefixes, and none imitates a real access-token format.
- Translation quality reflects one author. Native-speaker review is recommended, especially for mr, te, ur and bn (see concerns below).
- We do not claim the text appears nowhere else. The claim is limited to this authoring process.

## Chronology / holdout separation

1. The holdout tasks and holdout privacy were written first and frozen at 2026-11-09T01:21:26Z:
   - `tasks-holdout.json` sha256 `81506851cef58214e7179dccff85d0fe774c903da356247e52f7d544acbcd630`
   - `privacy-holdout.json` sha256 `41a520e309be679a2329c1bbb11ff42583a8ecbb76491cfe88c92dc7cf299113`
2. The development families were written next, with no access to holdout outcomes or engine output. They were finished at 2026-11-09T01:35:06Z. The holdout files are byte-identical to the frozen copies.
3. Families and scenario types never cross splits, and that includes translations. Every case has a unique `template_group`.

## Shared shape

Each file is `{schema_version:1, synthetic:true, corpus_version, cases:[...]}`. Each case carries the required fields plus some optional owner-side metadata: `family`, `kind`, `language_mode` (auto/explicit), `scenario`/`scenario_description` (privacy only), `policy_provenance`, `homonym_controls`, `nfd_spans`, and for tasks `reference_response`, `rubric_notes`, `missing_original_facts` and `max_points`.

- `echo_path`, `task_path` and every `secrets[].path`/`public[].path` are **relative to `payload`**: codex `["input",0,"content"]`, claude `["messages",0,"content"]`.
- Offsets are Python codepoint indices, end-exclusive, into the original string, which may contain deliberate NFD sequences.
- `forced_terms` lists exactly the surfaces of spans whose policy is `explicit` (owner-registered codenames). Contextual and pattern labels are gold-only and never forced.
- In `human_text`, each private span becomes a stable alias (`PERSON_1`, `ORG_1`, `PROJECT_1`, `TEAM_1`, `EMAIL_1`, `PHONE_1`, `ID_1`, `USER_1`, `HOST_1`). Mentions of the same identity share one alias even across inflection, script (e.g. 권새벽 / Saebyeok) or normalization (NFD vs NFC). All other text, including public homonym spans, stays verbatim.
- Privacy cases alternate codex/claude (51/51) and auto/explicit language mode (51/51) in each split. Task cases are codex, with modes 9 auto / 8 explicit.
- `reference_response`, `rubric_notes` and `missing_original_facts` are **owner-side only**. They must never be sent to the interpreter.

## Exact denominators

| File | Cases | Private occurrences | Public spans | explicit / pattern / contextual | forced terms | NFD private spans | Max rubric points per repeat |
|---|---|---|---|---|---|---|---|
| `tasks-holdout.json` | 17 | 64 | 0 | 1 / 8 / 55 | 1 | 0 | 68 |
| `privacy-holdout.json` | 102 | 747 | 282 | 34 / 323 / 390 | 34 | 29 | 0 |
| `tasks-development.json` | 17 | 71 | 0 | 0 / 5 / 66 | 0 | 0 | 68 |
| `privacy-development.json` | 102 | 786 | 186 | 68 / 272 / 446 | 68 | 33 | 0 |

The privacy splits together contain **204 cases and 1533 private occurrences**; the target was at least 1020. Each task split has 17 languages × 4 criteria, so the **theoretical** maximum is 68 points per repeat. That is a ceiling, not a guaranteed observed score. With 3 repeats the per-arm denominator is 204 points per split. The per-language breakdown is in `source-manifest.json`.

## Privacy scenario taxonomy and split manifest

**privacy-holdout.json** (6 scenarios × 17 languages):

- `H1`: clinic front-desk reschedule note (names, patient ref, phone, email, homonym controls)
- `H2`: configuration/code snippet with owner-registered codename (code-fence boundary)
- `H3`: support chat transcript with speaker labels and repeated mentions
- `H4`: CSV export rows (structured comma boundaries) with surname/given-name homonyms
- `H5`: forwarded email thread with quoted lines, mixed language, organization names, registered team codename
- `H6`: volunteer sign-up note where the same identity appears in NFD and NFC forms

**privacy-development.json** (6 scenarios × 17 languages):

- `D1`: HR performance note with mentor, organization, employee ID and homonym-name controls
- `D2`: application log lines (key=value, hostnames, usernames, account IDs) inside a code fence
- `D3`: product meeting minutes with several owner-registered project codenames that also occur as ordinary words
- `D4`: apartment viewing arrangement (agent, agency, unit ID, applicant) with repeated mentions
- `D5`: Markdown ticket checklist with backticks, @handles and a mixed-language comment
- `D6`: school-to-parent message with NFD-normalized names and NFD ordinary-word controls

Design notes:
- Every privacy case has at least 5 private occurrences and at least 1 public contrast span. Most cases pair a name that is also an ordinary word (Rose/rose, 하늘, Luz/luz, Deniz/deniz, Вера/вера, आशा, نور, 文静, 光 …) with an ordinary-word use of the same or an overlapping surface in the same text. `homonym_controls` records the automatically detected pairs. Inflected pairs (e.g. Заря/заре) are labelled but not auto-detected.
- Ordinary words are labelled public because of their **role in context**, not because the word is familiar. The same surface is private when it refers to a person. Identifying the role is the ambiguity under test.
- Explicit spans are owner-registered codenames: H2 config `project:` values, H5 team codenames, and the D3 project codenames. D3 deliberately repeats those codenames as ordinary nouns in other sentences (e.g. "Leuchtturm", "lantern", "маяк"). It tests whether a forced rule also over-masks ordinary usage, which a case-sensitive exact match should avoid.
- Boundaries covered: code fences (YAML/JSON/TOML/INI/.env), CSV rows, `key=value` logs, Markdown checklists, `@handles` and backticks, `>` quoted email lines, Turkish apostrophe suffixes, Arabic proclitics (لـ / و), CJK text with no spaces, and mixed scripts (e.g. Latin names inside Devanagari, English lines inside Korean).
- NFD coverage: H6 and D6 in every language put one identity in both NFD and NFC form (Hangul jamo, Latin diacritics, Cyrillic й/ё, Bengali ো, Arabic/Urdu آ/أ/إ, Telugu ై, kana dakuten, pinyin tones), and some public homonyms are also NFD.

## Task rubric policy

Each task has exactly four criteria, graded in English: `intent`, `conditions`, `prohibition`, `scope`.
- **Missing information is intentional** in some tasks (listed in `missing_original_facts`). A targeted clarification plus a conditional, usable draft gets full credit. If a decision genuinely needs an unavailable fact (a participant count, a delivery date, a purchase date), deferring that decision without inventing a value is correct. No rubric requires a concrete book list, material, room size or similar fact that the prompt lacks.
- Opaque aliases are not missing facts. The interpreter may see `PERSON_2` and can use it verbatim. Resolving or disclosing an original value is never required.
- Every task can be answered as plain text without tools. Not executing unavailable tools is never a failure.
- Paraphrasing the prompt back is not an answer. `intent` requires the requested artifact (roster, table, letter, list …) to exist in usable form.
- Every reference response can score 4/4: it preserves the requested order, negations, output scope and decision prerequisites. Where several answers are valid (seating plan, agenda positions 3–4), the rubric says that any valid answer earns credit.

## Development task references and rubric rationale

### `dev-task-en` (en, `development-task-release-note`)

Missing original facts: v4.3 date (not given; must not be invented)

- **intent**: Rewrites the internal bullets as a user-facing release note for version 4.2 of the named product.
- **conditions**: Two paragraphs in the requested order: first new features (dark mode); second the fixes (CSV leading zeros, emoji-folder rename crash) plus the move of offline sync to 4.3.
- **prohibition**: Mentions no ticket numbers and no staff names, and invents no release date for 4.3.
- **scope**: Exactly two paragraphs of release-note prose with no headings or extra commentary.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No release date for 4.3 exists in the original; stating only the version is correct.

Reference response (owner-side, theoretical 4/4):

```text
Lumenfold 4.2 introduces dark mode, so you can switch the whole app to a darker theme that is easier on the eyes in low light.

This release also fixes two issues: CSV exports now keep leading zeros, and the app no longer crashes when you rename a folder that contains an emoji. Offline sync, originally planned for this version, is now scheduled for version 4.3.
```

### `dev-task-ko` (ko, `development-task-dinner-vote-notice`)

Missing original facts: team lead's tie-break decision

- **intent**: Writes a team-channel notice summarizing the dinner-venue vote.
- **conditions**: Reports the 4–4–2 result with the Soban/Porta tie, the confirmed date/time (next Friday 7 pm), and that the tie is to be broken by team lead Oh Jeong-won (decision pending).
- **prohibition**: Reveals no individual votes and does not invent the team lead's decision or a final venue.
- **scope**: A notice of at most three sentences, with no extra commentary.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The tie-break decision is genuinely missing; saying it is pending is full credit.

Reference response (owner-side, theoretical 4/4):

```text
다음 주 금요일 저녁 7시 팀 회식 장소 투표 결과, 한식당 '소반'과 이탈리안 '포르타'가 각 4표로 동점이었고 일식 '하루'는 2표였습니다. 미리 정한 대로 최종 장소는 오정원 팀장님이 결정해 주실 예정입니다. 장소가 확정되는 대로 다시 공지드리겠습니다.
```

### `dev-task-es` (es, `development-task-speed-bump-letter`)

- **intent**: Writes a formal letter from the neighbourhood association to the city council requesting a speed bump on Calle Mirlo in front of the school.
- **conditions**: Includes both supporting facts (two minor pedestrian accidents in October; 63 signing neighbours), a respectful formal tone, the president's signature and contact email, and stays within 150 words.
- **prohibition**: Contains no threats of protests or media involvement.
- **scope**: Only the letter, without a subject line or address block.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
Estimados señores:

En nombre de la Asociación Vecinal Los Almendros, solicitamos la instalación de un reductor de velocidad en la calle Mirlo, frente al colegio. Durante el mes de octubre se produjeron dos atropellos leves en ese tramo, y nos preocupa la seguridad de los niños y de las familias que lo cruzan cada día. Esta petición cuenta con el respaldo de 63 vecinos firmantes.

Quedamos a su disposición para aportar cualquier información adicional y les agradecemos de antemano su atención.

Atentamente,
Pilar Montesinos
Presidenta de la Asociación Vecinal Los Almendros
pilar.montesinos@almendros-demo.invalid
```

### `dev-task-fr` (fr, `development-task-day-itinerary`)

Missing original facts: clock tower opening hours

- **intent**: Produces a Saturday day itinerary for Céleste and Tom covering the three named places.
- **conditions**: Starts with the market within 8:00–12:00, places the museum within 10:00–13:00, keeps lunch at 12:30–13:30 and schedules no visit overlapping lunch; the clock tower is placed tentatively.
- **prohibition**: Adds no extra places and invents no opening hours for the clock tower.
- **scope**: An hour-by-hour programme followed by exactly one line on what to verify (the tower's hours).

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Tower hours are genuinely unknown; a tentative slot plus a verification line is full credit.

Reference response (owner-side, theoretical 4/4):

```text
- 8 h 30 – 9 h 45 : marché couvert
- 10 h – 12 h 15 : musée de la Dentelle
- 12 h 30 – 13 h 30 : déjeuner
- À partir de 14 h (sous réserve) : tour de l'Horloge
À vérifier : les horaires d'ouverture de la tour de l'Horloge le samedi après-midi ; si elle est fermée, il faudra revoir la fin du programme.
```

### `dev-task-pt` (pt, `development-task-reading-quiz`)

- **intent**: Creates a four-question multiple-choice quiz about the given passage.
- **conditions**: Exactly four questions, each with options A–C, following the order of the passage and asking only about facts stated in it (distractor options may be invented).
- **prohibition**: Includes no answer key or marked correct answers.
- **scope**: Only the quiz itself, without introduction or explanations.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Distractors are necessarily invented and do not violate 'only facts from the text'; the question stems must be answerable from the passage.

Reference response (owner-side, theoretical 4/4):

```text
1. Em que ano a horta da escola foi criada?
A) 2017  B) 2019  C) 2021
2. Quem teve a iniciativa de criar a horta?
A) O zelador Benedito Assis  B) A diretora da escola  C) Os alunos do 5º ano
3. Quantos canteiros a horta tem hoje?
A) 8  B) 10  C) 12
4. O que é feito com a alface colhida?
A) É vendida na feira  B) É doada à cozinha da escola  C) É levada para casa pelos alunos
```

### `dev-task-de` (de, `development-task-shopping-sections`)

- **intent**: Sorts Wilma's shopping list into the four store sections.
- **conditions**: Every remaining item is in the correct section (Äpfel, Karotten / Milch, Joghurt / Brötchen, Vollkornbrot / Zahnpasta, Duschgel) with duplicates removed.
- **prohibition**: Butter (marked 'hab ich noch') is excluded and no items are added.
- **scope**: Only the four headings with items beneath them, no extra text.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
Obst & Gemüse
- Äpfel
- Karotten
Kühlregal
- Milch
- Joghurt
Backwaren
- Brötchen
- Vollkornbrot
Drogerie
- Zahnpasta
- Duschgel
```

### `dev-task-id` (id, `development-task-birthday-story`)

Missing original facts: child's age (deliberately withheld)

- **intent**: Writes a birthday story opening featuring Arunika.
- **conditions**: Includes cats and kites and features her older brother Bima; at most 100 words.
- **prohibition**: No frightening elements (ghosts, lost children, etc.) and no mention of the child's age.
- **scope**: Only a title and the story, no explanation.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The age is deliberately withheld and must not be stated; invented story details (e.g. a pet's name) are acceptable creative content.

Reference response (owner-side, theoretical 4/4):

```text
Layang-Layang Kucing Oranye
Pagi itu angin bertiup lembut di halaman rumah. Arunika membawa layang-layang baru bergambar kucing oranye, persis seperti Kumis, kucing kesayangannya. "Ayo, Kak Bima, bantu aku menerbangkannya!" serunya. Bima memegang benang sambil tertawa, lalu menghitung, "Satu, dua, tiga!" Layang-layang itu naik tinggi dan menari di antara awan putih. Kumis mengeong dari jendela seolah ikut bersorak. Hari itu terasa istimewa, karena setiap tarikan benang membawa Arunika semakin dekat pada kejutan ulang tahun yang sudah menunggunya.
```

### `dev-task-tr` (tr, `development-task-bill-split`)

- **intent**: Splits the dinner bill and states who owes Oğuz how much.
- **conditions**: Correct arithmetic: food 1,800 TL split four ways (450 TL each), drinks 600 TL split between Oğuz and Dilara (300 TL each); Ece 450 TL, Mert 450 TL, Dilara 750 TL owed to Oğuz.
- **prohibition**: Adds no tip and does not list Oğuz as owing himself.
- **scope**: Output is a list of debts (an optional one-line check is fine).

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
- Ece Arslan: 450 TL
- Mert Güler: 450 TL
- Dilara Koç: 750 TL
(Oğuz'un kendi payı 750 TL; toplam 2.400 TL tutuyor.)
```

### `dev-task-ru` (ru, `development-task-router-steps`)

- **intent**: Rewrites the router-restart instructions as simple steps for the neighbour.
- **conditions**: All five steps present in the original order with the details preserved (30 seconds, up to 2 minutes, green 'Интернет' light, call the grandson at the given number), addressed with formal «вы».
- **prohibition**: Adds no steps about settings or passwords.
- **scope**: Only a numbered list.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
1. Выдерните блок питания роутера из розетки.
2. Подождите 30 секунд.
3. Вставьте блок питания обратно в розетку.
4. Подождите до 2 минут, пока лампочка «Интернет» не загорится зелёным.
5. Если лампочка не загорелась зелёным, позвоните внуку Дмитрию по номеру +1 202 555 0189.
```

### `dev-task-hi` (hi, `development-task-lesson-outline`)

Missing original facts: whether a lab is available

- **intent**: Creates a 40-minute lesson-plan outline on water transport in plants for class 7.
- **conditions**: Four sections in the given order with times 5/15/10/10 minutes (the remainder correctly computed as 10), the celery-in-coloured-water experiment, and the co-teacher helping in the experiment.
- **prohibition**: Suggests no hazardous chemicals and does not assume the lab is available (works in a classroom or states a conditional alternative).
- **scope**: Only a table with the columns section, time, activity.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Lab availability is genuinely unknown; the plan must work either way.

Reference response (owner-side, theoretical 4/4):

```text
| खंड | समय | गतिविधि |
|---|---|---|
| परिचय | 5 मिनट | रेणु अग्रवाल प्रश्न से शुरुआत करेंगी: पौधे पानी को जड़ से पत्तियों तक कैसे पहुँचाते हैं? |
| प्रयोग | 15 मिनट | अनुराग सेठी की मदद से सेलेरी के डंठल को खाने वाले रंग मिले पानी में रखना और रंग को ऊपर चढ़ते देखना (प्रयोगशाला न मिले तो कक्षा की मेज़ पर) |
| चर्चा | 10 मिनट | छात्र बताएँगे कि रंग ऊपर क्यों चढ़ा और इसका पौधों में पानी के परिवहन से क्या संबंध है |
| सारांश और गृहकार्य | 10 मिनट | मुख्य बिंदुओं का सारांश; गृहकार्य: प्रयोग का चित्र बनाकर दो वाक्य लिखना |
```

### `dev-task-mr` (mr, `development-task-teacher-thanks`)

- **intent**: Writes a short thank-you note to the music teacher.
- **conditions**: Mentions both points (taught every Saturday for the whole year; Gargi's first solo song at the school gathering) in 4–6 sentences.
- **prohibition**: Makes no mention of a gift.
- **scope**: Only the note, ending with the exact sign-off 'आपली कृतज्ञ, माधवी ताम्हणकर'.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
आदरणीय शुभदा साने बाई,
वर्षभर दर शनिवारी गार्गीला मनापासून शिकवल्याबद्दल आपले खूप आभार. आपल्या मार्गदर्शनामुळे तिच्यात गाण्याची गोडी आणि आत्मविश्वास वाढला. शाळेच्या स्नेहसंमेलनात तिने पहिल्यांदाच एकटीने गाणे म्हटले, तो क्षण आमच्यासाठी अविस्मरणीय होता. यामागे आपली मेहनत आणि संयम आहे. पुन्हा एकदा मनःपूर्वक धन्यवाद.
आपली कृतज्ञ,
माधवी ताम्हणकर
```

### `dev-task-bn` (bn, `development-task-allergy-meal-plan`)

Missing original facts: budget (deliberately undecided)

- **intent**: Plans dinners for Monday to Wednesday for the visiting nephew.
- **conditions**: Each day includes at least one vegetarian dish; covers exactly Monday, Tuesday and Wednesday.
- **prohibition**: Contains no shrimp and no nuts (including nut-based gravies) and mentions no prices or costs.
- **scope**: Exactly three lines in the format 'day – dishes'.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Budget is deliberately undecided; no prices should appear and no clarification is needed.

Reference response (owner-side, theoretical 4/4):

```text
সোমবার – ভাত, মুসুর ডাল, আলু-পটলের তরকারি, ডিমের ঝোল
মঙ্গলবার – রুটি, ছোলার ডাল, পনিরের তরকারি, মাছের ঝোল
বুধবার – খিচুড়ি, বেগুন ভাজা, মিক্সড সবজি, মুরগির ঝোল
```

### `dev-task-ur` (ur, `development-task-club-faq`)

Missing original facts: annual fee amount (not yet approved)

- **intent**: Turns the club membership rules into an FAQ.
- **conditions**: Each answer is faithful to the stated rules (12-month membership; guests twice a month, always with the member; suspension request at least 15 days ahead to the secretary at the given email).
- **prohibition**: Adds no rule not in the source and states no fee amount (a fee question, if included, says the amount is not yet approved).
- **scope**: Exactly three question–answer pairs and nothing else.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The fee amount is genuinely missing; either omitting the fee or saying it is pending approval is full credit.

Reference response (owner-side, theoretical 4/4):

```text
س: رکنیت کتنی مدت کے لیے ہوتی ہے؟
ج: رکنیت 12 ماہ کے لیے ہوتی ہے۔
س: کیا میں مہمان لا سکتا ہوں؟
ج: جی ہاں، مہینے میں دو بار، اور ہر بار مہمان کو آپ کے ساتھ آنا ہوگا۔
س: رکنیت معطل کیسے کروائی جائے؟
ج: کم از کم 15 دن پہلے سیکرٹری فریحہ انصاری کو fariha.ansari@sarw-demo.invalid پر لکھیں۔
```

### `dev-task-te` (te, `development-task-recipe-scaling`)

- **intent**: Scales the pesarattu recipe from 4 to 10 servings.
- **conditions**: Every quantity multiplied by 2.5 correctly: 5 cups green gram, 1¼ cups rice, 10 green chillies, 5 inches ginger.
- **prohibition**: Salt stays 'to taste' (no number) and no ingredients are added.
- **scope**: Only an 'ingredient – quantity' list, without the author's name or extra steps.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
పెసలు – 5 కప్పులు
బియ్యం – 1¼ కప్పులు
పచ్చిమిర్చి – 10
అల్లం – 5 అంగుళాలు
ఉప్పు – రుచికి సరిపడా
```

### `dev-task-ar` (ar, `development-task-seating-plan`)

- **intent**: Produces a seating plan for the six named guests around the round table.
- **conditions**: All constraints hold on the circular table (seat 6 is adjacent to seat 1): Fatima in seat 1; Sami and Layla not adjacent; Youssef next to Hind; Tariq not in seat 2 or 6. Any valid arrangement earns credit.
- **prohibition**: Adds no people and omits none; each person appears exactly once.
- **scope**: Only a list numbered 1 to 6.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Several valid arrangements exist; graders must check constraints rather than match the reference.

Reference response (owner-side, theoretical 4/4):

```text
1. فاطمة الراوي
2. سامي الراوي
3. طارق ناصيف
4. ليلى الراوي
5. يوسف بركات
6. هند بركات
```

### `dev-task-zh` (zh, `development-task-landlord-message`)

- **intent**: Writes a WeChat message to the landlord asking for the bathroom-ceiling leak to be repaired.
- **conditions**: States the leak has lasted three days, that the upstairs neighbour reports no problem, and offers both time windows (Wednesday 7–9 pm; all Saturday morning); polite tone; at most 100 characters.
- **prohibition**: Does not mention rent reduction.
- **scope**: Only the message body.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
刘先生您好，我家卫生间天花板漏水已经三天了。楼上孙悦家说他们那边没有问题，想麻烦您安排师傅来检查维修。我在家的时间是周三晚上7点到9点，或者周六上午全天，您看哪个时间方便？谢谢！
```

### `dev-task-ja` (ja, `development-task-return-reply`)

Missing original facts: purchase date

- **intent**: Writes a reply to the customer's mug-return inquiry.
- **conditions**: Explains the policy, asks for the purchase date, and gives guidance for both cases (within 14 days: return accepted with receipt; beyond 14 days: not accepted).
- **prohibition**: Does not decide acceptance or refusal unconditionally and invents no purchase date.
- **scope**: Only the reply text, ending with the signature 'ひまわり雑貨店 岡田'.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The purchase date is genuinely missing; a conditional reply asking for it is full credit.

Reference response (owner-side, theoretical 4/4):

```text
藤井 涼 様

このたびはお問い合わせいただき、ありがとうございます。
当店では、ご購入から14日以内・未使用・レシートありの場合に返品を承っております。レシートをお持ちで未使用とのことですので、恐れ入りますがご購入日をお知らせいただけますでしょうか。
ご購入から14日以内であれば、商品とレシートをご持参いただければ返品を承ります。14日を過ぎている場合は、規定により返品をお受けできかねますので、あらかじめご了承ください。

ひまわり雑貨店 岡田
```

## Holdout task references and rubric rationale (OWNER-ONLY)

> Do not read this section while tuning against development results, and never send it to an interpreter. It is here because the coordinator asked for every reference in one owner-side document.

### `hold-task-en` (en, `holdout-task-volunteer-roster`)

Missing original facts: Hope Lindgren's availability

- **intent**: Produces a Saturday roster assigning the three named shifts among the three named volunteers.
- **conditions**: Respects every rule: Rose not on 8–11, Wes on 14–17 (the shift receiving the 14:00 truck), nobody on two consecutive shifts; the resulting assignment is Hope 8–11, Rose 11–14, Wes 14–17 (or the rule-compliant fallback offered conditionally).
- **prohibition**: Assigns no unnamed person and does not present Hope's availability as confirmed (her slot is marked pending/conditional).
- **scope**: Output is a three-line time-ordered list plus a targeted request about Hope's availability (an optional rule-compliant fallback is allowed); no unrelated content.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Hope's availability is genuinely absent from the original; a conditional roster plus a confirmation request is full credit. Refusing to produce any roster until Hope replies loses 'intent'.

Reference response (owner-side, theoretical 4/4):

```text
8–11: Hope Lindgren (pending her confirmation)
11–14: Rose Calloway
14–17: Wes Abara
Still needed: please confirm Hope can take 8–11. If she can't, the only arrangement within your rules is Wes on 8–11 and 14–17 (not consecutive) with Rose on 11–14, provided Wes agrees to two shifts.
```

### `hold-task-ko` (ko, `holdout-task-bookclub-notice`)

Missing original facts: the three selected book titles

- **intent**: Writes a Korean announcement for the library book club that includes the host, the schedule (second Saturday monthly, 3 pm, 2nd-floor seminar room) and how to apply (email to the host).
- **conditions**: Uses polite/honorific register (존댓말) throughout and stays within five sentences (a bracketed title line does not count as a sentence).
- **prohibition**: Does not invent book titles; states that the three books are still to be announced/undecided.
- **scope**: Returns only the notice body, with no preamble, alternatives or commentary.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Book titles are genuinely missing; a placeholder or 'to be announced' sentence is required, never a concrete list.

Reference response (owner-side, theoretical 4/4):

```text
[별다리 작은도서관 독서모임 안내] 매월 둘째 주 토요일 오후 3시, 2층 세미나실에서 독서모임을 엽니다. 진행은 윤하늘 님이 맡아 주십니다. 이번 분기 선정 도서 세 권은 위원회에서 확정되는 대로 따로 안내해 드리겠습니다. 참가를 원하시는 분은 윤하늘 님(haneul.yoon@byeoldari-demo.invalid)께 신청해 주세요.
```

### `hold-task-es` (es, `holdout-task-supplier-quote`)

Missing original facts: Mueblería Brisa's delivery date

- **intent**: Recommends between the two named suppliers for the 40 folding chairs.
- **conditions**: Applies the committee rule correctly: Brisa totals 1,815 € (65 € cheaper than Ondarra's 1,880 €), choosing Brisa is conditional on delivery before 15 March, and Ondarra (delivering 12 March) is the fallback.
- **prohibition**: Suggests no third supplier and does not invent a delivery date for Brisa.
- **scope**: Gives a one-sentence recommendation followed underneath by the calculations, and identifies the missing delivery date.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Brisa's delivery date is genuinely missing; an unconditional pick of either supplier loses 'conditions'.

Reference response (owner-side, theoretical 4/4):

```text
Recomendación: elegir Mueblería Brisa (1.815 € en total) solo si Nieves Arrieta confirma la entrega antes del 15 de marzo; si no puede confirmarlo, Talleres Ondarra (1.880 €, entrega el 12 de marzo).
Cálculos:
- Talleres Ondarra: 1.880 € con transporte incluido; entrega el 12/03, dentro del plazo.
- Mueblería Brisa: 1.720 € + 95 € = 1.815 €, es decir, 65 € más barata; fecha de entrega pendiente.
Dato que falta: la fecha de entrega de Mueblería Brisa.
```

### `hold-task-fr` (fr, `holdout-task-minutes-to-actions`)

Missing original facts: site-visit date (explicitly not set)

- **intent**: Converts the meeting minutes into an action-item table.
- **conditions**: Uses exactly the columns action / owner / deadline and keeps the three actions in their original order (contract review, intern badges, site-visit preparation), with joint ownership of the visit preserved.
- **prohibition**: Omits the budget discussion entirely and does not invent a deadline for the site visit (marked as not set).
- **scope**: Outputs only the table, covering exactly the three actions.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The site-visit date is explicitly unset in the original; 'non fixée'/'à définir' is correct.

Reference response (owner-side, theoretical 4/4):

```text
| Action | Responsable | Échéance |
|---|---|---|
| Relire le contrat de maintenance | Claire Fontanel | avant le 10 février |
| Commander les badges des stagiaires | Pierre Aubertin | 14 février |
| Préparer la visite du site Ardoise | Claire Fontanel et Manon Riguet | non fixée |
```

### `hold-task-pt` (pt, `holdout-task-discount-refusal`)

- **intent**: Writes a reply to Glória declining the 20% discount request on the named order.
- **conditions**: Courteous tone; explains the reason (8% only above 500 units, order has 320); offers free shipping; at most 90 words; signed as Vítor Cunha.
- **prohibition**: Promises no delivery date and grants no discount (not even the 8%).
- **scope**: Delivers only the message text addressed to the buyer.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. All facts needed are present; no clarification is expected.

Reference response (owner-side, theoretical 4/4):

```text
Olá, Glória,

Agradeço o contato em nome da Papelaria Alvorada. Infelizmente não podemos conceder 20% de desconto no pedido PED-SYN-5531: nossa política permite desconto de 8% apenas para pedidos acima de 500 unidades, e este pedido tem 320. Como alternativa, ofereço frete grátis para este pedido.

Fico à disposição.
Vítor Cunha
```

### `hold-task-de` (de, `holdout-task-fieldtrip-packing`)

- **intent**: Produces a packing list for the class day trip to the forest museum.
- **conditions**: Reflects all given constraints: rain gear, a packed lunch (no food on site) and a non-glass drink bottle.
- **prohibition**: Contains no medication, first-aid-medicine or medical-advice items.
- **scope**: Numbered list of at most eight items with no introduction or closing commentary.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts. Generic items beyond the constraints are fine if within eight.

Reference response (owner-side, theoretical 4/4):

```text
1. Regenjacke oder Regencape
2. Wasserfeste Schuhe
3. Lunchpaket für den ganzen Tag
4. Trinkflasche aus Kunststoff oder Metall (kein Glas)
5. Kleiner Rucksack
6. Wechselsocken
7. Schreibzeug für Notizen im Museum
8. Plastiktüte für nasse Sachen
```

### `hold-task-id` (id, `holdout-task-expense-categories`)

Missing original facts: tablecloth amount (receipt lost)

- **intent**: Groups the listed expenses into the three named categories with a subtotal for each.
- **conditions**: Correct assignment and arithmetic: Konsumsi Rp510.000; Perlengkapan Rp300.000 plus the unknown tablecloth; Transportasi Rp109.000; known total Rp919.000.
- **prohibition**: Does not guess or fill in the tablecloth amount; flags it as unknown/excluded.
- **scope**: A table followed by a single sentence stating the overall (known) total.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The tablecloth amount is genuinely missing; stating the total as known-portion-only is full credit.

Reference response (owner-side, theoretical 4/4):

```text
| Kategori | Item | Subtotal |
|---|---|---|
| Konsumsi | Nasi kotak; air mineral | Rp510.000 |
| Perlengkapan | Sewa tenda; taplak meja (jumlah belum diketahui) | Rp300.000 + taplak meja |
| Transportasi | Bensin mobil Pak Bulan Siswanto; ongkos ojek | Rp109.000 |

Total yang sudah diketahui adalah Rp919.000, belum termasuk taplak meja yang notanya hilang (mohon konfirmasi jumlahnya ke Bu Intan Wulandari).
```

### `hold-task-tr` (tr, `holdout-task-leave-handover`)

Missing original facts: new meeting date (pending)

- **intent**: Writes a handover note for Umut covering the user's pending items during their leave.
- **conditions**: Includes all three facts accurately: offer to Yıldırım Lojistik goes out Friday; Tuesday meeting with Deniz postponed with the new date pending; warehouse count completed.
- **prohibition**: Does not include the customer's phone number and does not invent a new meeting date.
- **scope**: Exactly three bullet points with no text before or after them.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The new meeting date is pending in the original; saying so is correct.

Reference response (owner-side, theoretical 4/4):

```text
- Yıldırım Lojistik'e teklif cuma günü gönderilecek.
- Deniz Ulu ile salı toplantısı ertelendi; yeni tarih henüz belli değil, gelince takvime işlenmeli.
- Depo sayımı tamamlandı, ek işlem gerekmiyor.
```

### `hold-task-ru` (ru, `holdout-task-room-booking`)

Missing original facts: number of workshop participants

- **intent**: Helps choose a meeting room for Vera's Thursday 10:00–13:00 workshop.
- **conditions**: Rules out Klyon (unavailable before 11:00) and gives the correct conditional choice: Olkha if ≤8 participants, Dub if 9–40.
- **prohibition**: Does not invent a participant count and does not commit to one room as if the count were known.
- **scope**: Short answer: a targeted request for the participant count plus the conditional decision; no booking procedure or unrelated advice.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. The room decision genuinely depends on the missing participant count; deferring it with a conditional rule is the correct answer.

Reference response (owner-side, theoretical 4/4):

```text
Нужно уточнить у Веры Синицыной число участников. «Клён» не подходит в любом случае — до 11:00 он занят. Если участников не больше 8 — бронируйте «Ольху»; если от 9 до 40 — «Дуб»; если больше 40, ни одна комната не подойдёт.
```

### `hold-task-hi` (hi, `holdout-task-parent-reminder`)

- **intent**: Writes a WhatsApp reminder to Class 4 parents about the parent-teacher meeting.
- **conditions**: Includes Saturday 10 am, the school hall, and the instruction to message the class teacher Pooja at the given number if unable to attend; under 60 words.
- **prohibition**: Makes no mention of pending or overdue fees.
- **scope**: Outputs only the message text.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
नमस्ते अभिभावकगण, कक्षा 4 की अभिभावक-शिक्षक बैठक शनिवार सुबह 10 बजे सरस्वती विहार विद्यालय के हॉल में होगी। कृपया समय पर पधारें। यदि आप नहीं आ सकते, तो कक्षा अध्यापिका पूजा रस्तोगी जी को +1 415 555 0144 पर संदेश भेजें। धन्यवाद।
```

### `hold-task-mr` (mr, `holdout-task-repair-priority`)

- **intent**: Orders the four society repair complaints by priority.
- **conditions**: Applies the rule exactly: safety first (Asha), then leaks by date (Kiran 4 March before Megha 6 March), then other (Vijay).
- **prohibition**: Adds no new complaints and alters no facts.
- **scope**: Numbered list only, each line with the name and a one-sentence reason.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
१. आशा नाईक – जिना अंधारात असल्याने हा सुरक्षिततेचा धोका आहे.
२. किरण दळवी – पाणी गळतीची तक्रार असून ती ४ मार्चला सर्वात आधी आली.
३. मेघा कर्वे – पाणी गळतीची तक्रार आहे, पण ती ६ मार्चला नंतर आली.
४. विजय साठे – आरशावरील डाग हा इतर प्रकारचा, कमी तातडीचा प्रश्न आहे.
```

### `hold-task-bn` (bn, `holdout-task-feedback-themes`)

- **intent**: Identifies the two most frequent themes in the cooking-workshop feedback.
- **conditions**: The themes are heat/ventilation (2 participants) and insufficient ingredients (2 participants), each stated with its count.
- **prohibition**: Includes no participant names and no verbatim quotes.
- **scope**: Exactly two bullets; the single positive teacher comment is not presented as a top theme.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
• ঘরের অতিরিক্ত গরম ও বাতাস চলাচলের অভাব — ২ জন।
• উপকরণ, বিশেষ করে সবজি, কম পড়া — ২ জন।
```

### `hold-task-ur` (ur, `holdout-task-delay-apology`)

Missing original facts: delay reason; new delivery date

- **intent**: Writes an apology email to Saba about the delayed order.
- **conditions**: Apologizes, says the cause and new date are still being determined, and commits to an update within 48 hours; signed by Noor Hassan.
- **prohibition**: Invents no delay reason or delivery date and offers no discount or compensation.
- **scope**: Outputs the email itself (subject/body/signature), referencing the order.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Reason and new date are genuinely missing; the correct answer explicitly defers them.

Reference response (owner-side, theoretical 4/4):

```text
موضوع: آرڈر ORD-SYN-2290 میں تاخیر

محترمہ صبا ملک صاحبہ،

ہمیں افسوس ہے کہ آپ کا آرڈر ORD-SYN-2290 وعدہ شدہ تاریخ پر نہیں پہنچ سکا۔ تاخیر کی وجہ ہم گودام سے معلوم کر رہے ہیں، اور ترسیل کی نئی تاریخ ابھی طے نہیں ہوئی۔ ہم 48 گھنٹوں کے اندر آپ کو تازہ صورتحال سے آگاہ کریں گے۔ اس زحمت کے لیے دلی معذرت۔

نیک خواہشات کے ساتھ،
نور حسن
```

### `hold-task-te` (te, `holdout-task-study-timetable`)

- **intent**: Creates a Monday–Friday 6–8 pm study timetable for Kiran.
- **conditions**: Maths on at least two days, Wednesday left free for cricket, exactly one subject per study day (with four study days, the natural solution also schedules physics and Telugu once each).
- **prohibition**: No Saturday/Sunday entries and no subject scheduled on Wednesday.
- **scope**: Exactly five 'day – subject' lines and nothing else (Wednesday's line marks it as free).

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts. Omitting physics or Telugu is not penalised under 'conditions' if every explicit rule holds, but graders may note it.

Reference response (owner-side, theoretical 4/4):

```text
సోమవారం – గణితం
మంగళవారం – భౌతికశాస్త్రం
బుధవారం – విరామం (క్రికెట్ ప్రాక్టీస్)
గురువారం – గణితం
శుక్రవారం – తెలుగు
```

### `hold-task-ar` (ar, `holdout-task-job-posting`)

Missing original facts: salary (not yet approved)

- **intent**: Drafts a job posting for the warehouse coordinator role at the named company.
- **conditions**: Includes the schedule (full time, Sunday–Thursday), the location, both requirements (two years' warehouse experience, forklift licence) and the application contact.
- **prohibition**: Contains no age or gender condition and no salary figure (saying salary will be announced later is fine).
- **scope**: Only the posting text: a title plus three short paragraphs.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. Salary is genuinely missing; it must not be invented.

Reference response (owner-side, theoretical 4/4):

```text
منسق مستودع – شركة النور للتوزيع

تبحث شركة النور للتوزيع عن منسق مستودع بدوام كامل من الأحد إلى الخميس في المنطقة الصناعية الثانية.

المتطلبات: خبرة لا تقل عن سنتين في المخازن، ورخصة قيادة رافعة شوكية سارية.

للتقديم، يُرجى مراسلة هدى الشامي على huda.alshami@alnoor-demo.invalid. سيُعلن عن تفاصيل الراتب لاحقًا.
```

### `hold-task-zh` (zh, `holdout-task-notice-proofread`)

- **intent**: Proofreads the notice draft against the stated facts and identifies the errors.
- **conditions**: Finds both discrepancies: weekday (星期日 → 星期六) and floor (二楼 → 三楼).
- **prohibition**: Does not rewrite the whole notice and does not 'correct' items that already match (date, time, organizer, email).
- **scope**: Numbered list in 'original → corrected' form only.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts. Mentioning that the event type is not among the stated facts is acceptable only if not presented as a correction.

Reference response (owner-side, theoretical 4/4):

```text
1. 星期日 → 星期六
2. 二楼 → 三楼
```

### `hold-task-ja` (ja, `holdout-task-agenda-order`)

- **intent**: Orders the five agenda items for next week's regular meeting.
- **conditions**: New-member introduction first, quote-comparison report second (Morishita leaves at 11), budget approval after the report, 'その他' last.
- **prohibition**: Adds no agenda items and drops none.
- **scope**: Numbered list only with no explanation; budget approval and inventory results may appear in either order at positions 3–4.

Rubric notes: Private names/IDs may appear to the interpreter as opaque aliases; using the alias verbatim is fully acceptable and resolving or disclosing the original value is never required. No missing facts.

Reference response (owner-side, theoretical 4/4):

```text
1. 新メンバー紹介（佐伯 空さん）
2. 見積もり比較の報告（森下 光さん）
3. 予算案の承認
4. 備品の棚卸し結果
5. その他
```

## Unresolved translation / rubric concerns

- One author wrote all 17 languages. Some homonym pairs are near-matches rather than exact surfaces, chosen to keep the grammar natural (mr मेघा/मेघ, कमल/कमळ, प्राजक्ता/प्राजक्त; te ప్రేమ+తో; ur صادق; ru Заря/заре). They are still useful for testing ambiguity, but native review is advised.
- Telugu and Marathi register and particle use (గారు, ताई) have not been checked by a native speaker.
- `holdout-task-study-timetable` (te) does not explicitly require every subject to be scheduled. The rubric notes how to treat a timetable that drops physics or Telugu.
- `development-task-reading-quiz` (pt) needs invented distractors. The rubric says distractors do not break the "only facts from the text" condition.
- `development-task-seating-plan` (ar) and `holdout-task-agenda-order` (ja) accept several valid answers, so graders must check the constraints rather than match the reference string.
- Character and word limits (zh ≤100 characters, hi <60 words, pt ≤90 words, es ≤150 words, id ≤100 words) are counted by graders without a fixed tokenizer. Borderline cases need a stated counting rule from the coordinator.
- Phone numbers mostly use the NANP and UK fictional ranges even in other locales, so local phone formats are under-represented.
- `language_mode` is metadata only. The coordinator decides how auto and explicit modes change execution.

## Regeneration

The author built these files with a private markup-to-JSON script (kept outside the repository) and checked them with an independent validator that reads only the emitted JSON. The validator checks offsets, overlaps, alias reconstruction of `human_text`, leakage of private values into `human_text` outside public spans, forced/explicit consistency, payload paths, balance, NFD coverage, fictional email/phone ranges, rubric IDs, and that no family or `template_group` crosses splits. The final run printed `VALIDATION OK`.
