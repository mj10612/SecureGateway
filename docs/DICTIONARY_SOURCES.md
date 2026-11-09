# Domain dictionary sources and review status

Collection date: **2026-11-09**. Dictionary schema 1, data version **1.0.1**.
The collection contains public terminology, not company documents, operational
parameters or information classified as secret. Matching a term is a local
protection policy decision; neither inclusion nor a source's subject category
determines whether a particular occurrence is confidential.

## Candidate collection and current usable scope

The source collection contains **46,234 candidate records**, including 776
additional official DARPA program-name records. These are source records, not
46,234 independently specialist-reviewed technical concepts. Wikidata includes
named products/platforms and fictional entities. CPC includes classification
clauses rather than dictionary headwords. NASA's hierarchy includes related
engineering subjects outside a narrow industry definition.

| Domain | Source records considered | Wikidata | NASA | CPC | DARPA |
| --- | ---: | ---: | ---: | ---: | ---: |
| Defense | 21,204 | 18,652 | 203 | 1,573 | 776 |
| Automotive | 18,762 | 6,460 | 88 | 12,214 | 0 |
| Semiconductor | 6,268 | 2,058 | 140 | 4,070 | 0 |

The dictionary protects component names, named systems/models and project/program
names, not only generic industry vocabulary. Source labels such as `Sukhoi Su-17`,
`Type 69 tank`, `Mikoyan-Gurevich MiG-21`, DARPA `Frosty` and Korean `보라매` must
not disappear merely because they contain capitals, numbers or proper names.

Public Wikidata/NASA/DARPA labels are admitted under an explicit **source-category
protection policy**, with attribution and a non-specialist review status. Known
fiction/toy/game strings, unhelpful short generic labels, control characters and
grammatical fragments are excluded. Such filtering does not prove that every
remaining source entity is a real-world system or that its translation is right.
Users enabling a domain accept its broad label protection and resulting possible
overmasking. This is not hidden as specialist certification.

Automatic CPC phrase extraction remains browse-only pending review. The editorial
bilingual core is separately compiled and has explicit subcomponent/project
categories; source-derived forms cannot silently enter an editorial concept.

The following counts are from the supplied collection and curator snapshot.
Regeneration may change them; generated document/manifest counts and hashes
identify the exact packaged revision.

| Domain | Included concepts | Pending concepts, browse only | Active editorial core | Active source labels | All matching forms | Active matching forms | English forms | Korean forms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Defense | 19,566 | 93 | 210 | 19,263 | 21,410 | 21,317 | 19,667 | 1,743 |
| Automotive | 7,188 | 678 | 46 | 6,464 | 8,358 | 7,680 | 7,216 | 1,142 |
| Semiconductor | 2,330 | 139 | 47 | 2,144 | 2,860 | 2,721 | 2,359 | 501 |

Defense includes **149 explicitly compiled subcomponent concepts** across twelve
component categories and **785 explicit public project/program concepts** (the
editorial projects plus admitted DARPA entries). Many additional Wikidata
labels are named models/platforms; no claim is made that all 19,263 source-label
concepts are distinct projects, independently verified real-world objects, or
individually approved technical translations.

Concept counts are unique within each domain by the curator's English label
key. They are not an ontology equivalence claim across domains. A matching form
is a language/spelling/case/boundary rule. Case-insensitive uppercase/title/lower
spellings are deduplicated under that matching policy. Acronyms, translations,
plurals and spacing variants must not be counted as additional concepts.

The proposed target of **specialist reviewing** at least 1,000 headwords per
domain is not complete. More than 1,000 candidates per domain were collected;
the much larger defense/source label sets are usable under the explicitly
requested category protection policy, not a claim of 1,000 expert approvals.
No domain specialist has certified either set. Counts must not substitute for coverage,
false-positive, privacy or actual LLM comprehension measurements.

## Source provenance and reuse

### Wikidata structured labels

- Source: [Wikidata Query Service](https://query.wikidata.org/sparql), selected
  entity labels and Korean labels from relevant subclass/part trees.
- Structured main-namespace data is provided under **CC0 1.0**, according to
  [Wikidata's licensing policy](https://www.wikidata.org/wiki/Wikidata:Licensing).
  Wikipedia article prose and other-namespace text are not included.
- Attribution retained: **Wikidata contributors**, structured entity labels,
  retrieved 2026-11-09. Each retained label carries its Q identifier/source link.
- Limitations: missing translations, ambiguous class membership, fictional
  subjects and erroneous labels are possible. Named models are deliberately
  protected, not treated as contamination solely for being proper nouns. Korean
  source labels can be active under the same source policy but are not certified
  translations. Promoting an editorial English concept uses only its explicitly
  compiled core forms, not every attached source translation.

### NASA Thesaurus

- Data: [NASA Thesaurus CSV/Text](https://sti.nasa.gov/docs/thesaurus/thesaurus-CSV.txt).
- The [NASA NTRS data record](https://ntrs.nasa.gov/citations/20120015349) identifies
  this as a US government work with public use permitted. The CSV/Text collection
  provides subject terms and relationships; definitions/scope notes are not used.
- Attribution retained: **NASA STI Program. (2012). NASA thesaurus [CSV/Text data
  file].** [NASA Thesaurus](https://sti.nasa.gov/nasa-thesaurus/).
- Modification: domain hierarchy selection, lexical filtering and deduplication
  of labels. NASA does not endorse this dictionary or its masking decisions.
- Factual component and model/program labels retain capitals, digits and
  punctuation. No family of identifiers is fabricated from a numbering pattern.
- Limitations: the aerospace-oriented hierarchy is not an exhaustive automotive,
  defense or semiconductor glossary. Related terms can be broader than the
  intended domain. Product names can be protected under the selected domain;
  unrelated subjects still require review.

### DARPA public program names

- Source: the official [program catalog](https://www.darpa.mil/research/programs)
  and its public [program listing JSON](https://www.darpa.mil/json/program.json),
  used by the site's own program-card interface. The collected 776 unique title
  records retain only node ID, factual title and official program-page URL.
- Attribution: **Defense Advanced Research Projects Agency (DARPA), public
  program names, retrieved 2026-11-09.** The
  [DARPA usage policy](https://www.darpa.mil/policies/usage-policy) requests source
  acknowledgement, excludes third-party works and prohibits endorsement claims.
  This collection uses factual title labels, not descriptions, personnel records,
  third-party illustrations, logos, operational parameters or trademark branding.
- Individual official records include [Frosty](https://www.darpa.mil/research/programs/frosty),
  [LongShot](https://www.darpa.mil/research/programs/longshot),
  [Manta Ray](https://www.darpa.mil/research/programs/manta-ray) and
  [ANCILLARY](https://www.darpa.mil/research/programs/advanced-aircraft-infrastructure-less-launch-and-recovery).
  Completed and current programs are both useful name-protection inputs. Their
  inclusion does not assert present operational status or program success.
- Short acronyms and single-word program names keep exact case to reduce
  ordinary-word collisions. Longer multiword names support case-insensitive
  matching; runtime boundaries must prevent matching inside unrelated words.

### Cooperative Patent Classification

- Source revision: **CPC 2026.08**, official
  [classification title ZIP](https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCTitleList202608.zip).
  Defense candidates use F41/F42; automotive B60/B62D/F02; semiconductor
  H01L/H10/G03F.
- The [CPC linked-data page](https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/CPCopenLinkedData)
  identifies the CPC scheme as part of Linked open EP data. The
  [EPO conditions](https://www.epo.org/en/searching-for-patents/data/linked-open-data)
  specify **Creative Commons Attribution 4.0 International** for that product.
  The downloaded title list is treated as the corresponding scheme label data;
  this basis does not extend to unrelated patent publications or website text.
- Attribution retained: **European Patent Office and United States Patent and
  Trademark Office, Cooperative Patent Classification, 2026.08; CC BY 4.0.**
  [License](https://creativecommons.org/licenses/by/4.0/).
- Modifications: select category titles; split semicolon-separated labels; remove
  scheme markup, references and explanatory tails; retain short contiguous
  candidate phrases; filter and deduplicate. No new technical phrase is created
  by concatenating distant title fragments. Definitions are not copied.
- Classification titles are not necessarily dictionary terms. Extracted prefixes
  can lose qualifiers or contain grammatical fragments; they remain browse-only
  until further review. The attribution/license/modification notices accompany
  redistributed source-derived data; the repository's Apache license does not
  replace these source notices.

### Independently compiled bilingual core

The expanded core consists of factual technical names and independently compiled Korean
forms/acronyms by SecureGateway contributors, under the repository's Apache-2.0
license. No third-party explanatory definitions or restricted dictionary
translations were copied. Each entry records its editorial category and any
matching collected source IDs. An editorial repository reference is a provenance
record, not evidence that a standards body has approved a translation.

Primary public references for the added defense scope include:

| Scope | Public primary reference | Used factual evidence |
| --- | --- | --- |
| Korean aircraft/program names and avionics components | [KAI's filed 2024 business report](https://kind.krx.co.kr/external/2025/03/18/001423/20250318006615/11011.htm) | KF-21/KF-X, T-50/FA-50, KUH-1/수리온, LAH-1/미르온; onboard computers and power control/distribution components |
| Korean fighter program | [DAPA KF-21 program page](https://www.dapa.go.kr/dapa/page/selectPage.do?menuSeq=3211&pageSeq=3208) | Public project identity; no nonpublic design data |
| KT-1/웅비 | [KAI virtual fixed-wing exhibition](https://www.koreaaero.com/VIRTUAL_EX/CorporateZone/FixedWing.html) | Public model and Korean name |
| Ground systems/project labels | [Hanwha Aerospace land products](https://www.hanwhaaerospace.com/kor/whatwedo/product/land.do) | 천무, 천마, 비호복합, K9/K10/K21 and publicly listed launch/support systems |
| 천검/TAipers | [DAPA development announcement](https://dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=16247&menuSeq=3069) | Public Korean/English missile program name |
| Radar projects and modules | [Hanwha Systems multifunction radar](https://www.hanwhasystems.com/kr/business/defense/isr/radar01.do) | 천궁/철매-II, KF-21 AESA, FFX-III, L-SAM, transmit/receive and digital modules |
| Actuation subassemblies | [Moog missile systems brochure](https://www.moog.com/content/dam/moog/literature/sdg/defense/moog-missile-systems-brochure.pdf) | Fin/wing actuation and servo-control subject matter |
| Connectors/harness interconnects | [TE Aerospace Connectors](https://www.te.com/en/products/connectors/intersection/aerospace-connectors.html) | Circular/rectangular, filtered, rugged high-speed and aerospace interconnect component families |
| Navigation/sensing | [NASA guidance/navigation/control survey](https://www.nasa.gov/smallsat-institute/sst-soa/guidance-navigation-and-control/) | Inertial sensors, gyros, accelerometers, navigation receivers, reaction wheels and pointing sensors |
| Thermal subcomponents | [NASA thermal-control survey](https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/) | Public heat-transfer/cooling component vocabulary |
| Flight computers/avionics | [NASA Avionics and Software](https://www.nasa.gov/reference/avionics-and-software/) | Public flight avionics, command/telemetry and control-system subject matter |

These references ground factual subject/name checks; explanatory sentences,
images, numerical operating characteristics and restricted source definitions
are not incorporated. The sources do not certify every independently translated
Korean component form or this project's protection policy. No private domestic
project names or operational details were sought.

Short acronyms are case-sensitive. They may have multiple technical or ordinary
meanings: enabling a domain intentionally protects matching occurrences. Terms
such as systems engineering, battery management and automatic test equipment
are dual-use; their inclusion is a policy choice, not automatic secret detection.

### Excluded restricted source

The [Korean defense terminology dataset](https://www.data.go.kr/data/3058147/fileData.do)
advertises 16,279 rows. Its captured primary metadata stated **KOGL Type 4**
(attribution, noncommercial, no derivatives), despite a third-party aggregator's
CC0 claim. Its rows were **not imported into the candidate pool or derived
dictionary**. A publicly viewable page does not establish permission to copy,
translate or redistribute its content under Apache-2.0.

## Category coverage and gaps

| Domain | Editorial core coverage | Material gaps |
| --- | --- | --- |
| Defense | Base core 41; explicit subcomponents 149 across radar/sensors, seeker/optics/radome, actuator/servo, power, boards/computers, connector/harness, RF, navigation, structure, thermal, fuze and data buses; editorial public projects 20; public named-source inventory and DARPA program labels | Specialist/individual source entity review, validated translations and completeness of parts catalogs; no nonpublic supplier part-number catalogs |
| Automotive | Powertrain (6), electrification (7), battery/thermal management (7), chassis (4), ADAS (6), electronics/network/software (7), safety/quality (5), manufacturing (4) | Korean source coverage is sparse; detailed production/supply-chain and component terms need review; classification clauses must not be activated as headwords |
| Semiconductor | Devices (5), memory (4), design/verification (7), materials (5), fabrication (8), lithography (3), metrology (4), packaging (6), test (3), production (2) | Validated specialist translations, process/measurement details and manufacturing tracking coverage; automatic device/product classes can be misleading |

The source shortlist's Q/CPC categories are traceability fields, not a reviewed
coverage taxonomy. Current dictionaries start with Korean/English; they do not
provide equivalent technical dictionaries for all 17 supported prose languages.

## Reproduce and inspect

Use the three captured `DOMAIN-candidates.json` files, the additional
`defense-extra-labels.json` containing the sanitized DARPA labels, and their source manifest.
The collection is an offline build input, not a request-time download:

```sh
uv run python scripts/curate_domain_dictionaries.py \
  --source-dir /path/to/secure-gateway-dictionary-sources \
  --output /path/to/domain-preview
```

Each output records the candidate bytes' SHA-256, curator source SHA-256,
exclusion counts, review status, activation status, language/case/boundary rules
and source references. `manifest.json` pins dictionary bytes/version/counts.
No pickle, executable model or runtime source query is used.

Review tests identified and removed obvious false headwords, including fictional
spacecraft terminology, a game-item label, relative vehicle clauses, a dangling
semiconductor preposition and title fragments such as `Capacitor integral`.
This is evidence of why automatic filtering is insufficient, not a claim that
the remaining active source labels or shortlist have no errors. Source labels
carry `active-source-category-reviewed-not-specialist-certified` review metadata
and `active-source-label` activation status; the editorial core has
`active-editorial-core` activation status. Automatic CPC extraction retains
`browse-only-pending-review` status. Protecting public names under a domain is
different from certifying the names or inferring that an occurrence is secret.
Review source corrections and additional candidates by checking
term boundaries, translations, ambiguity and actual privacy/overmasking/
comprehension results; retain their source and change history.

The source snapshot additionally includes 6,306 automotive Wikidata labels from the motor-car hierarchy. Compressed raw candidate files and their uncompressed hashes are archived in `dictionary-sources/2026-11-09/`; decompress into a temporary source folder before reproducing. These are protected public model/component names, not 6,306 newly specialist-reviewed technical components.
