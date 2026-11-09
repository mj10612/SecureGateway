"""Build bounded, reproducible domain dictionaries from attributed candidate pools.

This is lexical/editorial curation, not specialist certification. No network access,
definitions, generated phrase combinations, runtime downloads, or quota filling.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata


SCHEMA_VERSION = 1
DICTIONARY_VERSION = "1.0.0"
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_CANDIDATES = 100_000
MAX_ENTRIES = 30_000
MAX_FORMS = 100_000
MAX_TERM_CHARS = 256
DOMAINS = ("defense", "automotive", "semiconductor")
SOURCES = {
    "wikidata": {
        "name": "Wikidata structured entity labels", "license": "CC0-1.0",
        "url": "https://www.wikidata.org/",
        "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
        "attribution": "Wikidata contributors; structured main-namespace labels, retrieved 2026-11-09.",
        "modifications": "Selected labels only; no article prose or definitions.",
    },
    "nasa": {
        "name": "NASA Thesaurus CSV/Text", "license": "US-Government-Work",
        "url": "https://sti.nasa.gov/docs/thesaurus/thesaurus-CSV.txt",
        "license_url": "https://ntrs.nasa.gov/citations/20120015349",
        "attribution": "NASA STI Program. (2012). NASA thesaurus [CSV/Text data file]. https://sti.nasa.gov/nasa-thesaurus/",
        "modifications": "Selected subject labels; CSV/Text contains no definitions or scope notes. No NASA endorsement.",
    },
    "cpc": {
        "name": "CPC 2026.08 scheme titles / Linked open EP data", "license": "CC-BY-4.0",
        "url": "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCTitleList202608.zip",
        "license_url": "https://www.epo.org/en/searching-for-patents/data/linked-open-data",
        "license_scope_url": "https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/CPCopenLinkedData",
        "attribution": "European Patent Office and United States Patent and Trademark Office, Cooperative Patent Classification, 2026.08; CC BY 4.0. https://creativecommons.org/licenses/by/4.0/",
        "modifications": "Extracted short contiguous noun-phrase prefixes from classification titles; removed scheme markup/references; selected and deduplicated. No classification definitions copied.",
    },
    "editorial": {
        "name": "SecureGateway bilingual core terminology", "license": "Apache-2.0",
        "url": "https://github.com/mj10612/SecureGateway",
        "attribution": "SecureGateway contributors, 2026. Independently compiled factual terminology and Korean translations; no third-party explanatory text.",
        "modifications": "Editorial seed list, not a translation of a restricted dictionary or specialist validation.",
    },
    "darpa": {
        "name": "DARPA public research program names", "license": "Public factual labels; DARPA informational use policy",
        "url": "https://www.darpa.mil/json/program.json",
        "license_url": "https://www.darpa.mil/policies/usage-policy",
        "attribution": "Defense Advanced Research Projects Agency (DARPA), public program title/ID/link labels, retrieved 2026-11-09. No DARPA/DoD endorsement.",
        "modifications": "Retained factual program titles and links only; removed descriptions, personnel, imagery, operational parameters and other metadata. No logos or third-party works.",
    },
}

# Own-authored factual headwords and translations; no manufacturer definitions.
# Short acronyms are separately case-sensitive and retain an ambiguity warning.
SEEDS = {
    "defense": """
command|command and control|지휘통제|C2
command|command control communications computers intelligence surveillance and reconnaissance|지휘통제통신컴퓨터정보감시정찰|C4ISR
command|battle management system|전장관리체계|BMS
command|tactical data link|전술데이터링크|TDL
command|tactical communications|전술통신|
sensor|phased-array radar|위상배열레이더|
sensor|active electronically scanned array|능동위상배열레이더|AESA
sensor|synthetic aperture radar|합성개구레이더|SAR
sensor|electro-optical sensor|전자광학센서|EO
sensor|infrared search and track|적외선탐색추적장치|IRST
sensor|electro-optical infrared|전자광학적외선|EO/IR
electronic_warfare|electronic warfare|전자전|EW
electronic_warfare|electronic support measures|전자지원책|ESM
electronic_warfare|electronic countermeasures|전자대응책|ECM
electronic_warfare|electronic counter-countermeasures|전자대대응책|ECCM
navigation|inertial navigation system|관성항법장치|INS
navigation|global navigation satellite system|위성항법시스템|GNSS
navigation|integrated navigation system|복합항법장치|
navigation|missile seeker|유도무기탐색기|
platform|unmanned aerial vehicle|무인항공기|UAV
platform|unmanned ground vehicle|무인지상차량|UGV
platform|unmanned surface vehicle|무인수상정|USV
platform|unmanned underwater vehicle|무인잠수정|UUV
platform|mission payload|임무탑재체|
protection|active protection system|능동방호체계|APS
protection|identification friend or foe|피아식별|IFF
protection|radar cross section|레이더반사단면적|RCS
engineering|systems engineering|체계공학|
engineering|requirements management|요구도관리|
engineering|configuration management|형상관리|
engineering|operational test and evaluation|운용시험평가|OT&E
engineering|developmental test and evaluation|개발시험평가|DT&E
engineering|electromagnetic compatibility|전자기적합성|EMC
support|integrated logistics support|종합군수지원|ILS
support|life cycle management|수명주기관리|
support|performance upgrade|성능개량|
acquisition|defense acquisition|방위사업획득|
acquisition|technology transfer|기술이전|
acquisition|offset agreement|절충교역|
quality|defense quality assurance|국방품질보증|
quality|supply chain assurance|공급망보증|
""",
    "automotive": """
powertrain|powertrain|파워트레인|
powertrain|drivetrain|구동계|
powertrain|torque converter|토크컨버터|
powertrain|dual-clutch transmission|듀얼클러치변속기|DCT
powertrain|limited-slip differential|차동제한장치|LSD
powertrain|reduction gearbox|감속기|
electrification|traction motor|구동모터|
electrification|traction inverter|구동인버터|
electrification|on-board charger|온보드차저|OBC
electrification|DC-DC converter|직류직류변환기|
electrification|regenerative braking|회생제동|
electrification|vehicle-to-grid|차량전력망연계|V2G
electrification|vehicle-to-load|차량외부전력공급|V2L
battery|battery management system|배터리관리시스템|BMS
battery|battery state of charge|배터리충전상태|SOC
battery|battery state of health|배터리건전상태|SOH
battery|battery cooling circuit|배터리냉각회로|
battery|battery thermal management|배터리열관리|
battery|battery module|배터리모듈|
battery|battery pack|배터리팩|
chassis|anti-lock braking system|잠김방지제동장치|ABS
chassis|electronic stability control|차체자세제어장치|ESC
chassis|electric power steering|전동식파워스티어링|EPS
chassis|independent suspension|독립현가장치|
adas|advanced driver assistance system|첨단운전자보조시스템|ADAS
adas|automatic emergency braking|자동긴급제동|AEB
adas|adaptive cruise control|적응형순항제어|ACC
adas|lane keeping assist|차선유지보조|LKA
adas|blind spot detection|사각지대감지|BSD
adas|sensor fusion|센서융합|
electronics|electronic control unit|전자제어장치|ECU
electronics|vehicle control unit|차량제어기|VCU
electronics|transmission control unit|변속기제어기|TCU
electronics|controller area network|차량제어통신망|CAN
electronics|controller area network flexible data rate|가변전송률차량제어통신망|CAN FD
electronics|automotive ethernet|차량용이더넷|
electronics|software-defined vehicle|소프트웨어중심자동차|SDV
safety|safety of the intended functionality|의도된기능의안전성|SOTIF
safety|diagnostic trouble code|진단고장코드|DTC
safety|on-board diagnostics|차량자가진단|OBD
safety|failure mode and effects analysis|고장형태영향분석|FMEA
safety|noise vibration and harshness|소음진동불쾌감|NVH
manufacturing|body-in-white|차체골격|BIW
manufacturing|automotive stamping die|자동차프레스금형|
manufacturing|automotive spot welding|자동차점용접|
manufacturing|vehicle durability testing|차량내구시험|
""",
    "semiconductor": """
device|semiconductor|반도체|
device|metal oxide semiconductor field effect transistor|금속산화막반도체전계효과트랜지스터|MOSFET
device|fin field effect transistor|핀형전계효과트랜지스터|FinFET
device|gate-all-around field effect transistor|게이트올어라운드전계효과트랜지스터|GAAFET
device|complementary metal oxide semiconductor|상보형금속산화막반도체|CMOS
memory|dynamic random-access memory|동적랜덤접근메모리|DRAM
memory|static random-access memory|정적랜덤접근메모리|SRAM
memory|high bandwidth memory|고대역폭메모리|HBM
memory|NAND flash memory|낸드플래시메모리|NAND
design|register transfer level|레지스터전송수준|RTL
design|electronic design automation|전자설계자동화|EDA
design|static timing analysis|정적타이밍분석|STA
design|design rule checking|설계규칙검사|DRC
design|layout versus schematic|레이아웃회로비교검증|LVS
design|process design kit|공정설계키트|PDK
design|place and route|배치배선|
material|silicon wafer|실리콘웨이퍼|
material|silicon carbide|탄화규소|SiC
material|gallium nitride|질화갈륨|GaN
material|photoresist|포토레지스트|
material|chemical mechanical polishing slurry|화학기계연마슬러리|
fabrication|ion implantation|이온주입|
fabrication|plasma etching|플라즈마식각|
fabrication|reactive ion etching|반응성이온식각|RIE
fabrication|atomic layer deposition|원자층증착|ALD
fabrication|chemical vapor deposition|화학기상증착|CVD
fabrication|physical vapor deposition|물리기상증착|PVD
fabrication|chemical mechanical planarization|화학기계평탄화|CMP
fabrication|epitaxial growth|에피택셜성장|
lithography|extreme ultraviolet lithography|극자외선노광|EUV
lithography|deep ultraviolet lithography|심자외선노광|DUV
lithography|optical proximity correction|광근접효과보정|OPC
metrology|critical dimension metrology|임계치수계측|CD
metrology|overlay metrology|오버레이계측|
metrology|film thickness measurement|박막두께측정|
metrology|statistical process control|통계적공정관리|SPC
packaging|through-silicon via|실리콘관통전극|TSV
packaging|wafer-level packaging|웨이퍼레벨패키징|WLP
packaging|wire bonding|와이어본딩|
packaging|flip-chip bonding|플립칩본딩|
packaging|semiconductor interposer|반도체인터포저|
packaging|chiplet|칩렛|
testing|automatic test equipment|자동시험장비|ATE
testing|wafer probing|웨이퍼프로빙|
testing|semiconductor burn-in testing|반도체번인시험|
production|semiconductor foundry|반도체파운드리|
production|semiconductor lot tracking|반도체로트추적|
""",
}

# Actual component names and public program labels, never numeric combinations
# generated to fill a quota. These bilingual forms are independently compiled;
# primary references establish the public subject matter, not certification of
# every Korean translation or the confidentiality of an occurrence.
SEEDS["defense"] += """
component_sensor|radar antenna|레이더안테나|
component_sensor|antenna array|배열안테나|
component_sensor|radiating element|복사소자|
component_sensor|transmit receive module|송수신모듈|TRM
component_sensor|digital transmit receive module|디지털송수신모듈|DTRM
component_sensor|radar exciter|레이더여기기|
component_sensor|radar receiver|레이더수신기|
component_sensor|radar signal processor|레이더신호처리기|
component_sensor|radar data processor|레이더자료처리기|
component_sensor|radar power amplifier|레이더전력증폭기|
component_sensor|radar antenna pedestal|레이더안테나구동대|
component_sensor|radar calibration unit|레이더교정장치|
component_seeker|active radar seeker|능동레이더탐색기|
component_seeker|seeker|탐색기|
component_seeker|semi-active radar seeker|반능동레이더탐색기|
component_seeker|passive radar seeker|수동레이더탐색기|
component_seeker|infrared seeker|적외선탐색기|
component_seeker|imaging infrared seeker|영상적외선탐색기|IIR
component_seeker|laser seeker|레이저탐색기|
component_seeker|seeker gimbal|탐색기김벌|
component_seeker|seeker detector|탐색기검출기|
component_seeker|focal plane array|초점면배열|FPA
component_seeker|optical window|광학창|
component_seeker|radome|레이돔|
component_seeker|seeker dome|탐색기돔|
component_actuator|electromechanical actuator|전기기계식구동기|EMA
component_actuator|actuator|구동장치|
component_actuator|electrohydraulic actuator|전기유압식구동기|EHA
component_actuator|fin actuator|조종날개구동기|
component_actuator|control actuation system|조종구동장치|CAS
component_actuator|thrust vector control actuator|추력편향제어구동기|
component_actuator|servo motor|서보모터|
component_actuator|servo controller|서보제어기|
component_actuator|servo valve|서보밸브|
component_actuator|rotary actuator|회전구동기|
component_actuator|linear actuator|선형구동기|
component_actuator|position transducer|위치변환기|
component_actuator|resolver|리졸버|
component_actuator|rotary encoder|회전엔코더|
component_actuator|ball screw|볼스크루|
component_power|power supply unit|전원공급장치|PSU
component_power|power distribution unit|전력분배장치|PDU
component_power|power conditioning unit|전력조절장치|PCU
component_power|power control and distribution unit|전력조절분배장치|PCDU
component_power|thermal battery|열전지|
component_power|reserve battery|예비전지|
component_power|battery activation device|전지활성화장치|
component_power|voltage regulator|전압조정기|
component_power|DC-DC converter|직류직류변환기|
component_power|electromagnetic interference filter|전자파간섭필터|EMI filter
component_power|solid-state power controller|반도체전력제어기|SSPC
component_power|power switching module|전력스위칭모듈|
component_board|printed circuit board|인쇄회로기판|PCB
component_board|printed circuit assembly|인쇄회로조립체|PCA
component_board|single-board computer|단일보드컴퓨터|SBC
component_board|mission computer|임무컴퓨터|
component_board|flight control computer|비행제어컴퓨터|FCC
component_board|guidance computer|유도컴퓨터|
component_board|onboard computer|탑재컴퓨터|OBC
component_board|digital signal processor|디지털신호처리기|DSP
component_board|field-programmable gate array|현장프로그래머블게이트어레이|FPGA
component_board|analog-to-digital converter|아날로그디지털변환기|ADC
component_board|digital-to-analog converter|디지털아날로그변환기|DAC
component_board|backplane|백플레인|
component_board|line replaceable unit|현장교환가능장치|LRU
component_board|built-in test equipment|내장시험장치|BITE
component_connector|circular connector|원형커넥터|
component_connector|rectangular connector|직사각형커넥터|
component_connector|coaxial connector|동축커넥터|
component_connector|fiber optic connector|광섬유커넥터|
component_connector|filtered connector|필터커넥터|
component_connector|connector backshell|커넥터백셸|
component_connector|hermetic connector|기밀커넥터|
component_connector|connector contact|커넥터접점|
component_connector|cable assembly|케이블조립체|
component_connector|wire harness|와이어하니스|
component_connector|coaxial cable|동축케이블|
component_connector|shielded twisted pair|차폐연선|
component_connector|cable shield|케이블차폐체|
component_rf|low-noise amplifier|저잡음증폭기|LNA
component_rf|high-power amplifier|고출력증폭기|HPA
component_rf|solid-state power amplifier|반도체전력증폭기|SSPA
component_rf|traveling-wave tube amplifier|진행파관증폭기|TWTA
component_rf|phase shifter|위상변위기|
component_rf|frequency synthesizer|주파수합성기|
component_rf|local oscillator|국부발진기|
component_rf|frequency mixer|주파수혼합기|
component_rf|frequency multiplier|주파수체배기|
component_rf|RF switch|고주파스위치|
component_rf|RF attenuator|고주파감쇠기|
component_rf|RF circulator|고주파서큘레이터|
component_rf|RF isolator|고주파아이솔레이터|
component_rf|directional coupler|방향성결합기|
component_rf|power divider|전력분배기|
component_rf|duplexer|듀플렉서|
component_rf|diplexer|다이플렉서|
component_rf|band-pass filter|대역통과필터|
component_rf|waveguide|도파관|
component_rf|monolithic microwave integrated circuit|모놀리식마이크로파집적회로|MMIC
component_navigation|inertial measurement unit|관성측정장치|IMU
component_navigation|gyroscope|자이로스코프|
component_navigation|fiber optic gyroscope|광섬유자이로스코프|FOG
component_navigation|ring laser gyroscope|링레이저자이로스코프|RLG
component_navigation|accelerometer|가속도계|
component_navigation|magnetometer|자력계|
component_navigation|GNSS receiver|위성항법수신기|
component_navigation|GNSS antenna|위성항법안테나|
component_navigation|star tracker|별추적기|
component_navigation|sun sensor|태양센서|
component_navigation|radar altimeter|레이더고도계|
component_navigation|air data computer|대기자료컴퓨터|
component_navigation|pitot tube|피토관|
component_navigation|reaction wheel|반작용휠|
component_structure|missile airframe|유도탄기체|
component_structure|control fin|조종날개|
component_structure|tail fin|꼬리날개|
component_structure|wing spar|날개주보|
component_structure|structural bulkhead|구조격벽|
component_structure|equipment bay|장비실|
component_structure|avionics rack|항공전자장비랙|
component_structure|vibration isolator|진동절연기|
component_structure|launch canister|발사관|
component_structure|launch tube|발사튜브|
component_structure|nose cone|노즈콘|
component_structure|composite sandwich panel|복합재샌드위치패널|
component_thermal|cold plate|냉각판|
component_thermal|heat sink|방열판|
component_thermal|heat pipe|히트파이프|
component_thermal|heat exchanger|열교환기|
component_thermal|liquid cooling loop|액체냉각회로|
component_thermal|cryocooler|극저온냉각기|
component_thermal|coolant pump|냉각수펌프|
component_thermal|thermal interface material|열전달계면재료|TIM
component_fuze|proximity fuze|근접신관|
component_fuze|impact fuze|충격신관|
component_fuze|electronic fuze|전자신관|
component_fuze|time fuze|시한신관|
component_fuze|safe and arm device|안전장전장치|S&A
component_fuze|arming mechanism|장전기구|
component_fuze|fuze setter|신관설정기|
component_fuze| fuze power supply|신관전원공급장치|
component_bus|MIL-STD-1553 data bus|MIL-STD-1553데이터버스|MIL-STD-1553
component_bus|ARINC 429 data bus|ARINC429데이터버스|ARINC 429
component_bus|ARINC 664 network|ARINC664네트워크|ARINC 664
component_bus|avionics full-duplex switched ethernet|항공전자전이중스위치드이더넷|AFDX
component_bus|SpaceWire data link|스페이스와이어데이터링크|SpaceWire
component_bus|serial remote terminal|직렬원격단말|
component_bus|bus controller|버스제어기|
component_bus|remote terminal|원격단말|
project_kai|KF-21 Boramae|보라매|KF-21,KF-X,IF-X
project_kai|KUH-1 Surion|수리온|KUH-1,SURION
project_kai|LAH-1 Mirion|미르온|LAH-1,MIRION
project_kai|KT-1 Woongbi|웅비|KT-1
project_kai|T-50 Golden Eagle|골든이글|T-50,TA-50,FA-50
project_kai|KAI Surion maritime helicopter|흰수리|KUH-1CG
project_aircraft|General Dynamics F-16 Fighting Falcon|F-16 파이팅 팰컨|F-16
project_aircraft|Lockheed Martin F-35 Lightning II|F-35 라이트닝 II|F-35
project_ground|K2 Black Panther|K2 흑표|K2
project_hanwha|K239 Chunmoo|천무|K239,CHUNMOO
project_hanwha|K9 Thunder|K9자주포|K9,K9A1,K9A2
project_hanwha|K10 ammunition resupply vehicle|K10탄약운반장갑차|K10
project_hanwha|K21 infantry fighting vehicle|K21보병전투장갑차|K21
project_hanwha|Chunma surface-to-air missile|천마|CHUNMA
project_hanwha|Biho hybrid air defense system|비호복합|BIHO
project_hanwha|Cheongeom air-to-ground missile|천검|TAipers
project_radar|Cheongung medium-range surface-to-air missile|천궁|천궁-II,철매-II,M-SAM
project_radar|long-range surface-to-air missile|장거리지대공유도무기|L-SAM
project_radar|Korean fighter AESA radar|한국형전투기AESA레이더|
project_radar|FFX-III multifunction radar|FFX-III다기능레이더|FFX-III
"""

PRIMARY_REFERENCES = {
    "component_sensor": "https://www.hanwhasystems.com/kr/business/defense/isr/radar01.do",
    "component_seeker": "https://kind.krx.co.kr/external/2026/03/23/001725/20260323007318/11011.htm",
    "component_actuator": "https://www.moog.com/content/dam/moog/literature/sdg/defense/moog-missile-systems-brochure.pdf",
    "component_power": "https://kind.krx.co.kr/external/2025/03/18/001423/20250318006615/11011.htm",
    "component_board": "https://www.nasa.gov/reference/avionics-and-software/",
    "component_connector": "https://www.te.com/en/products/connectors/intersection/aerospace-connectors.html",
    "component_rf": "https://www.hanwhasystems.com/kr/business/defense/isr/radar01.do",
    "component_navigation": "https://www.nasa.gov/smallsat-institute/sst-soa/guidance-navigation-and-control/",
    "component_structure": "https://kind.krx.co.kr/external/2025/03/18/001423/20250318006615/11011.htm",
    "component_thermal": "https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/",
    "component_fuze": "https://www.hanwhaaerospace.com/eng/whoweare/location/domestic.do",
    "component_bus": "https://www.te.com/en/products/connectors/intersection/aerospace-connectors.html",
    "project_kai": "https://kind.krx.co.kr/external/2025/03/18/001423/20250318006615/11011.htm",
    "project_aircraft": "https://www.lockheedmartin.com/en-us/products/f-16.html",
    "project_ground": "https://www.hyundai-rotem.co.kr/en/business/defense/details.do?productCt03=defense0101",
    "project_hanwha": "https://www.hanwhaaerospace.com/kor/whatwedo/product/land.do",
    "project_radar": "https://www.hanwhasystems.com/kr/business/defense/isr/radar01.do",
}
SOURCES["editorial"]["primary_references"] = PRIMARY_REFERENCES

TECHNICAL_CUES = {
    "defense": frozenset("radar missile torpedo gun guns cannon artillery ballistic armor armoured armored naval military tactical electronic warfare guided guidance inertial navigation acoustic antenna sonar submarine unmanned ammunition munition munitions projectile fuze fuse propellant breech barrel recoil firing weapon weapons firearm firearms reconnaissance surveillance logistics countermeasure countermeasures aircraft airframe aerospace naval radar-directed".split()),
    "automotive": frozenset("automotive automobile car vehicle motor engine piston combustion crankshaft camshaft cylinder clutch gearbox transmission brake brakes braking steering suspension differential torque axle wheel wheels tyre tyres tire tires exhaust manifold catalytic ignition injector injection carburetor carburettor powertrain drivetrain traction battery charging charger regenerative airbag seatbelt seatbelts headlamp headlight chassis vehicle-to-grid lithium cooling turbocharger alternator wiper windscreen windshield automotive".split()),
    "semiconductor": frozenset("semiconductor transistor transistors diode diodes silicon wafer wafers lithography photoresist photolithography photomask photomasks reticle reticles epitaxial epitaxy planarization metallization implant implantation etching etch plasma deposition sputtering dopant doping dielectric interconnect interconnects integrated circuit circuits microelectronic microelectronics microcontroller microprocessor photodiode phototransistor thyristor rectifier capacitor memory flash nanosheet nanowire quantum CMOS MOSFET FinFET HBM NAND DRAM SRAM GaN SiC".casefold().split()),
}
GENERIC = frozenset("model system control cell pack platform process device equipment material method apparatus means component element mechanism manufacturing production preparation details accessories assembly arrangement installation type version other parts part unit body structure surface tool tools connector converter switch driver board module bearing memory filter coupling coating support management communication navigation receiver transmitter power motor engine wheel tire battery seal fuel sensor signal testing information computer electronic semiconductor integrated circuit electrical technology quality reliability requirements configuration performance development defense automotive military normal general special conventional portable used safety machine data cooling guide guides friction hydraulic mechanical optical pneumatic precision automatic digital analog hand operated electric radiation characteristics masks originals coating thereof therefor".split())
DENY_PHRASES = frozenset({"control system", "electronic equipment", "electrical equipment", "military equipment", "vehicle component", "vehicle components", "systems engineering", "power supply", "signal processing", "data processing", "radio communication", "control unit", "engine parts", "metal coating", "electric vehicles", "electronic circuits", "integrated circuits", "semiconductor devices"})
RELATIVE_START = re.compile(r"^(?:a |an |the |of |in |on |at |by |to |from |within |through |outside |during |for |with |without |having |using |being |adapted |characteri[sz]ed |specially |comprising |including |relating |involving |other |said |such |wherein |thereof|therefor|containing |carrying |mounted |combined |formed |provided |multiple |further |mainly |generally |partly |suitable |means |combinations |arrangements |use |adjustment |constructional |dimensions |connections |openings |end mounts )", re.I)
CLAUSE = re.compile(r"\s+(?:characteri[sz]ed|using|for|with|having|adapted|comprising|including|consisting|wherein|being|in which|specially)\b|,\s*(?:e\.g\.?|i\.e\.?)", re.I)
HANGUL = re.compile(r"^[가-힣][가-힣 -]{2,95}$")
VERBAL_HEADS = frozenset("adjusting advancing retarding checking detecting controlling stabilising stabilizing constructing pressurisation pressurization permitting preventing effecting actuating maintaining reducing increasing selecting regulating connecting combining providing singulating manufacturing manufacture simultaneous electrically specially indirectly directly mechanically hydraulically pneumatically manually".split())
NON_DOMAIN_EXAMPLES = frozenset({"potato cannon", "t-shirt cannon", "air cannon", "confetti cannon", "toy gun", "toy guns", "toy pistol", "water gun", "water pistol", "military lucky draw box", "military spacecraft"})
NON_HEADWORD = re.compile(
    r"^(?:into |onto |upon |arranged |formation |cleaning |special features |arrangement |"
    r"[a-z-]+ (?:applying|controlling|comprising|having|using) )"
    r"|\b(?:per se|in (?:military|naval|air force) service|in the vehicle)\b"
    r"|\b(?:integral|integrated|thereof|therefor)$", re.I
)
FICTIONAL_OR_GAME = re.compile(r"\b(?:fictional|fantasy|game|gaming|loot|lucky draw|toy|confetti|water pistol)\b", re.I)
FICTIONAL_NAMES = re.compile(r"\b(?:star wars|star trek|warhammer|warcraft|war thunder|world of tanks|battlefield game|gundam|pokemon|pokémon|transformers|lego|titanfall|halo universe|firefly universe|battlestar|starcraft|mass effect|space battleship)\b|우주전함|건담|게임아이템|게임 아이템", re.I)


def canonical(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _source_ref(row: dict) -> dict:
    identifier, source = row["id"], row["source"]
    if source == "wikidata":
        url = "https://www.wikidata.org/wiki/" + identifier
    elif source == "cpc":
        url = "https://data.epo.org/linked-data/def/cpc/" + identifier.removeprefix("cpc:").replace(" ", "").replace("/", "-")
    elif source == "darpa":
        url = row.get("url", "")
        if not isinstance(url, str) or not re.fullmatch(r"https://www\.darpa\.mil/research/programs/[A-Za-z0-9-]+(?:/[A-Za-z0-9-]+)*", url):
            raise ValueError("Invalid DARPA program source URL.")
    else:
        url = SOURCES["nasa"]["url"]
    return {"source": source, "id": identifier, "url": url, "category": row.get("category", "unspecified")}


def _noun_phrases(row: dict):
    text = row.get("en")
    if not isinstance(text, str):
        return
    if row["source"] == "cpc":
        for fragment in text.split(";"):
            # Scheme braces are editorial markup; retain an actual contiguous
            # text prefix, never join distant title fragments into a new term.
            fragment = fragment.strip().strip("{}").strip()
            fragment = re.split(r"[([{]", fragment, maxsplit=1)[0]
            fragment = CLAUSE.split(fragment, maxsplit=1)[0]
            yield canonical(fragment).strip(" ,.;:-")
    else:
        yield canonical(text)


def _reject_reason(text: str, domain: str, source: str) -> str | None:
    if source in {"wikidata", "nasa", "darpa"}:
        # Factual model/program/component names are protected policy inputs.
        # Case and digits are evidence, not reasons to discard F-16/AN/APG-81.
        # Source category review is intentionally distinct from expert or
        # independent item-by-item verification.
        if not 2 <= len(text) <= MAX_TERM_CHARS or any(unicodedata.category(c).startswith("C") for c in text):
            return "length-or-control-character"
        if not any(c.isalpha() for c in text):
            return "not-a-label"
        if len(text) <= 2 and not any(c.isdigit() for c in text):
            return "short-ambiguous-label"
        lower = text.casefold()
        if lower in NON_DOMAIN_EXAMPLES or FICTIONAL_OR_GAME.search(text) or FICTIONAL_NAMES.search(text):
            return "fictional-or-game-context"
        if lower in GENERIC or lower in {"air", "land", "sea", "water", "space", "vehicle", "vehicles", "equipment"}:
            return "generic-or-ambiguous"
        if RELATIVE_START.match(text) or NON_HEADWORD.search(text):
            return "classification-not-a-headword"
        return None
    if not 3 <= len(text) <= MAX_TERM_CHARS:
        return "length"
    if not re.fullmatch(r"[A-Za-z][A-Za-z -]*[A-Za-z]", text):
        return "digits-or-nonlexical"
    words = text.split()
    if len(words) < 2 or len(words) > 7:
        return "not-specific-noun-phrase"
    if RELATIVE_START.match(text) or CLAUSE.search(text):
        return "relative-or-verbal-fragment"
    # Uppercase named models/acronyms are only admitted via the explicit seed
    # list; capitalization is a conservative filter, not an entity detector.
    if source != "cpc" and any(char.isupper() for char in text):
        return "proper-name-or-acronym-needs-review"
    lower = text.casefold()
    if lower.split()[0] in VERBAL_HEADS or " permitting " in lower or " during " in lower or " without " in lower:
        return "relative-or-verbal-fragment"
    if " or " in lower or " and " in lower:
        return "multiple-concepts-or-relative-fragment"
    if lower in NON_DOMAIN_EXAMPLES:
        return "out-of-domain-or-toy"
    if FICTIONAL_OR_GAME.search(lower):
        return "fictional-or-game-context"
    if NON_HEADWORD.search(text):
        return "classification-not-a-headword"
    if lower in DENY_PHRASES or all(word in GENERIC for word in lower.split()):
        return "generic-or-ambiguous"
    tokens = set(re.findall(r"[a-z]+(?:-[a-z]+)*", lower))
    if not tokens.intersection(TECHNICAL_CUES[domain]):
        return "no-domain-cue"
    if any(word in tokens for word in {"thereof", "therefor", "thereto", "respectively", "namely", "suitable", "specifically", "particularly", "precedence"}):
        return "relative-or-verbal-fragment"
    if lower.endswith((" and", " or", " of", " to", " in", " by", " a", " an", " the")):
        return "truncated-fragment"
    return None


def _form(text: str, language: str, acronym=False) -> dict:
    return {"text": canonical(text), "language": language,
            "case_sensitive": bool(acronym), "boundary": "hangul" if language == "ko" else "word"}


def _entry(domain: str, english: str, category: str) -> dict:
    digest = sha256((domain + "\0" + english.casefold()).encode()).hexdigest()[:20]
    return {"id": domain + "-" + digest, "forms": [], "category": category,
            "source_refs": [], "review_status": "automatic-source-and-lexical-review",
            "ambiguity": "Domain policy term; not a determination that an occurrence is confidential. Specialist review pending."}


def _add_form(entry: dict, form: dict) -> None:
    def identity(value):
        text = value["text"] if value["case_sensitive"] else value["text"].casefold()
        return value["language"], text, value["case_sensitive"], value["boundary"]
    if not any(identity(existing) == identity(form) for existing in entry["forms"]):
        entry["forms"].append(form)


def curate(domain: str, rows: list[dict]) -> dict:
    if len(rows) > MAX_CANDIDATES:
        raise ValueError("Candidate count exceeds curation budget.")
    entries, rejected = {}, Counter()
    source_counts = Counter()
    source_by_label = {}
    for row in rows:
        if (not isinstance(row, dict) or row.get("source") not in {"wikidata", "nasa", "cpc", "darpa"}
                or not isinstance(row.get("id"), str) or len(row["id"]) > 128):
            raise ValueError("Malformed candidate source record.")
        patterns = {"wikidata": r"Q\d+", "nasa": r"nasa:\d+", "cpc": r"cpc:[A-HY]\d{2}(?:[A-Z](?:\d+/\d+)?)?", "darpa": r"darpa:\d+"}
        if not re.fullmatch(patterns[row["source"]], row["id"]):
            raise ValueError("Invalid source identifier.")
        source_counts[row["source"]] += 1
        if isinstance(row.get("en"), str):
            source_by_label.setdefault(canonical(row["en"]).casefold(), []).append(row)
        for phrase in _noun_phrases(row):
            reason = _reject_reason(phrase, domain, row["source"])
            if reason:
                rejected[reason] += 1
                continue
            key = phrase.casefold()
            entry = entries.setdefault(key, _entry(domain, phrase, str(row.get("category", "unspecified"))))
            source_active = row["source"] in {"wikidata", "nasa", "darpa"}
            if source_active and entry["review_status"] == "automatic-source-and-lexical-review":
                # Automatic CPC prefixes do not become reviewed synonyms when
                # an independent factual source supplies the same label.
                entry["forms"] = []
                entry["review_status"] = "active-source-category-reviewed-not-specialist-certified"
                entry["ambiguity"] = "Public source-category component/model/program label; not independent item verification, translation certification, or a secrecy determination. Names can have ordinary meanings."
            elif not source_active and entry["review_status"] != "automatic-source-and-lexical-review":
                ref = _source_ref(row)
                if ref not in entry["source_refs"]:
                    entry["source_refs"].append(ref)
                continue
            short_or_program_word = len(phrase) <= 5 or row["source"] == "darpa" and " " not in phrase
            _add_form(entry, _form(phrase, "en", acronym=source_active and short_or_program_word and not phrase.islower()))
            ref = _source_ref(row)
            if ref not in entry["source_refs"]:
                entry["source_refs"].append(ref)
            # Only carry the Korean label when the entire entity label passed;
            # an extracted CPC prefix has no verified translation attached.
            korean = row.get("ko")
            if (row["source"] == "wikidata" and isinstance(korean, str)
                    and 2 <= len(canonical(korean)) <= MAX_TERM_CHARS
                    and not any(unicodedata.category(c).startswith("C") for c in korean)
                    and not FICTIONAL_NAMES.search(korean) and not FICTIONAL_OR_GAME.search(korean)):
                _add_form(entry, _form(korean, "ko"))
    for line in SEEDS[domain].strip().splitlines():
        if not line.strip():
            continue
        category, english, korean, acronyms = (piece.strip() for piece in line.split("|"))
        key = english.casefold()
        entry = entries.setdefault(key, _entry(domain, english, category))
        # Promotion admits only independently compiled core forms. An automatic
        # source's attached translation is not implicitly reviewed by matching
        # an editorial English headword.
        if entry["review_status"] != "editorial-bilingual-core-not-specialist-certified":
            entry["forms"] = []
        entry["category"] = category
        entry["review_status"] = "editorial-bilingual-core-not-specialist-certified"
        entry["ambiguity"] = "Acronyms and dual-use terms can have other meanings; enabled domain protects matching occurrences. Korean core forms are independently compiled translations."
        _add_form(entry, _form(english, "en"))
        _add_form(entry, _form(korean, "ko"))
        for acronym in filter(None, acronyms.split(",")):
            language = "ko" if any("가" <= char <= "힣" for char in acronym) else "en"
            _add_form(entry, _form(acronym, language, acronym=True))
        own_ref = {"source": "editorial", "id": domain + ":" + category + ":" + entry["id"], "url": PRIMARY_REFERENCES.get(category, SOURCES["editorial"]["url"]), "category": category}
        if own_ref not in entry["source_refs"]:
            entry["source_refs"].append(own_ref)
        for row in source_by_label.get(key, []):
            ref = _source_ref(row)
            if ref not in entry["source_refs"]:
                entry["source_refs"].append(ref)
    output = sorted(entries.values(), key=lambda entry: entry["id"])
    for entry in output:
        entry["activation_status"] = (
            "active-editorial-core" if entry["review_status"] == "editorial-bilingual-core-not-specialist-certified"
            else "active-source-label" if entry["review_status"] == "active-source-category-reviewed-not-specialist-certified"
            else "browse-only-pending-review"
        )
        entry["forms"].sort(key=lambda form: (form["language"], form["text"], form["case_sensitive"]))
        entry["source_refs"].sort(key=lambda ref: (ref["source"], ref["id"]))
    form_count = sum(len(entry["forms"]) for entry in output)
    if len(output) > MAX_ENTRIES or form_count > MAX_FORMS:
        raise ValueError("Curated dictionary exceeds output budget.")
    if len({entry["id"] for entry in output}) != len(output):
        raise ValueError("Stable ID collision.")
    for entry in output:
        if not entry["source_refs"] or not entry["forms"]:
            raise ValueError("Entry lacks provenance or match forms.")
        for form in entry["forms"]:
            if not 2 <= len(form["text"]) <= MAX_TERM_CHARS or any(unicodedata.category(c).startswith("C") for c in form["text"]):
                raise ValueError("Invalid curated matching form.")
    return {"schema_version": SCHEMA_VERSION, "id": domain, "version": DICTIONARY_VERSION,
            "default_enabled": domain == "defense", "sources": SOURCES, "entries": output,
            "counts": {"candidate_records": len(rows), "candidate_records_by_source": dict(sorted(source_counts.items())),
                       "concept_count": len(output), "form_count": form_count,
                       "unique_matching_strings": len({f["text"] for e in output for f in e["forms"]}),
                       "forms_by_language": dict(sorted(Counter(f["language"] for e in output for f in e["forms"]).items())),
                       "lexical_exclusions": dict(sorted(rejected.items())),
                       "editorial_core_concepts": sum(bool(line.strip()) for line in SEEDS[domain].splitlines()),
                       "active_concepts": sum(e["activation_status"].startswith("active-") for e in output),
                       "pending_concepts": sum(e["activation_status"] == "browse-only-pending-review" for e in output),
                       "active_forms": sum(len(e["forms"]) for e in output if e["activation_status"].startswith("active-")),
                       "active_source_label_concepts": sum(e["activation_status"] == "active-source-label" for e in output),
                       "defense_component_concepts": sum(e["category"].startswith("component_") for e in output),
                       "explicit_project_concepts": sum(e["category"].startswith("project_") or any(r["source"] == "darpa" for r in e["source_refs"]) for e in output)},
            "limits": {"max_candidates": MAX_CANDIDATES, "max_entries": MAX_ENTRIES,
                       "max_forms": MAX_FORMS, "max_term_chars": MAX_TERM_CHARS},
            "activation_policy": "Active editorial core and public source-category labels are eligible for runtime matching. Automatic CPC phrase candidates remain browse-only. Active source status is not expert certification or individual real-world verification.",
            "review_note": "Deterministic source/lexical filters plus an editorial bilingual core. Not domain-expert certification, exhaustive coverage, legal secrecy classification, or measured privacy/comprehension improvement."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="Folder containing DOMAIN-candidates.json files.")
    parser.add_argument("--output", type=Path, required=True, help="Explicit output folder; never changes host settings.")
    args = parser.parse_args()
    documents = {}
    for domain in DOMAINS:
        source = args.source_dir / (domain + "-candidates.json")
        if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("Candidate file missing, linked, or over size budget.")
        with source.open("rb") as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            raise ValueError("Candidate file grew beyond size budget.")
        value = json.loads(data)
        if not isinstance(value, dict) or value.get("domain") != domain or not isinstance(value.get("entries"), list):
            raise ValueError("Candidate file domain/schema mismatch.")
        extra = args.source_dir / (domain + "-extra-labels.json")
        extra_data = b""
        if extra.exists():
            if extra.is_symlink() or not extra.is_file() or extra.stat().st_size > MAX_SOURCE_BYTES:
                raise ValueError("Extra label file missing, linked, or over size budget.")
            extra_data = extra.read_bytes()
            if len(extra_data) > MAX_SOURCE_BYTES:
                raise ValueError("Extra label file grew beyond size budget.")
            extra_value = json.loads(extra_data)
            if (not isinstance(extra_value, dict) or extra_value.get("domain") != domain
                    or not isinstance(extra_value.get("entries"), list)):
                raise ValueError("Extra label file domain/schema mismatch.")
            value["entries"].extend(extra_value["entries"])
        document = curate(domain, value["entries"])
        document["candidate_sha256"] = sha256(data).hexdigest()
        if extra_data:
            document["extra_labels_sha256"] = sha256(extra_data).hexdigest()
        document["curator_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
        documents[domain] = document
    # Validate all inputs/output before publishing any dictionary.
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": SCHEMA_VERSION, "domains": {}}
    for domain, document in documents.items():
        data = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        destination = args.output / (domain + ".json")
        if destination.is_symlink():
            raise ValueError("Output dictionary must not be a symbolic link.")
        destination.write_bytes(data)
        counts = document["counts"]
        manifest["domains"][domain] = {"file": destination.name, "sha256": sha256(data).hexdigest(),
                                         "version": DICTIONARY_VERSION, "concept_count": counts["concept_count"],
                                         "form_count": counts["form_count"], "active_concepts": counts["active_concepts"],
                                         "pending_concepts": counts["pending_concepts"], "active_forms": counts["active_forms"],
                                         "active_source_label_concepts": counts["active_source_label_concepts"],
                                         "defense_component_concepts": counts["defense_component_concepts"],
                                         "explicit_project_concepts": counts["explicit_project_concepts"]}
        print(domain + ": " + json.dumps(counts, sort_keys=True))
    destination = args.output / "manifest.json"
    if destination.is_symlink():
        raise ValueError("Output manifest must not be a symbolic link.")
    destination.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
