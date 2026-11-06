"""Independently authored words for ordinary household and daily-life context.

This deliberately small supplement was written without consulting existing
vocabulary lists or test examples. It covers common words and selected everyday
inflections, not complete languages or a general-purpose safety classification.
"""

HOUSEHOLD_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        """
        cook cooking cooked bake baking boil boiling fry frying roast
        rice bread flour butter cheese milk yogurt eggs chicken fish
        soup salad potatoes tomatoes onions garlic carrots apples bananas salt
        sugar oil water bottle jar fridge freezer pantry shelf container
        lid leftovers thaw frozen fresh ripe wash washing laundry detergent
        rinse dry drying towel clothes shirt socks shoes umbrella rain
        rainy wind windy sunny cloudy jacket bag keys bicycle tire
        tires wheel wheels brake brakes chain pump pressure car battery
        garden soil plant plants pot seeds leaves flowers watering spring
        summer autumn winter season walk walking stretch stretching exercise workout
        calendar appointment tomorrow morning evening bedtime sleep sleeping rest nap
        clean cleaning broom mop dust vacuum dishes sponge soap rubbish
        """.split()
    ),
    "ko": frozenset(
        """
        요리 요리하다 요리해 끓이다 끓여 끓는 굽다 구워 볶다 볶아
        밥 쌀 빵 밀가루 버터 치즈 우유 달걀 계란 닭고기
        생선 국 수프 샐러드 감자 토마토 양파 마늘 당근 사과
        바나나 소금 설탕 기름 물 병 냉장고 냉동실 찬장 선반
        용기 뚜껑 남은 해동 냉동 신선한 익은 씻다 씻어 세탁
        빨래 세제 헹구다 헹궈 말리다 말려 수건 옷 셔츠 양말
        신발 우산 비 빗물 바람 맑은 흐린 겉옷 가방 열쇠
        자전거 타이어 바퀴 브레이크 체인 펌프 공기압 자동차 배터리 정원
        흙 식물 화분 씨앗 잎 꽃 물뿌리개 봄 여름 가을
        겨울 계절 걷기 걷다 걸어 스트레칭 운동 달력 약속 내일
        아침 저녁 잠자리 잠 자다 자고 휴식 낮잠 청소 청소하다
        빗자루 걸레 먼지 청소기 설거지 스펀지 비누 쓰레기 정리 닦아
        """.split()
    ),
    "es": frozenset(
        """
        cocinar cocinando cocido hornear hervir hirviendo freír asar arroz pan
        harina mantequilla queso leche yogur huevos pollo pescado sopa ensalada
        patatas tomates cebollas ajo zanahorias manzanas plátanos sal azúcar aceite
        agua botella tarro nevera congelador despensa estante recipiente tapa sobras
        descongelar congelado fresco maduro lavar lavando ropa detergente enjuagar secar
        secando toalla camisa calcetines zapatos paraguas lluvia lluvioso viento soleado
        nublado chaqueta bolsa llaves bicicleta neumático rueda freno cadena bomba
        presión coche batería jardín tierra planta plantas maceta semillas hojas
        flores regar primavera verano otoño invierno estación caminar caminando estirar
        ejercicio entrenamiento calendario cita mañana tarde noche dormir durmiendo descanso
        siesta limpiar limpiando escoba fregona polvo aspiradora platos esponja jabón
        basura ordenar fregar barrer lavado seco húmedo salir paseo horario
        """.split()
    ),
    "fr": frozenset(
        """
        cuisiner cuisine cuire cuit cuisson bouillir bouillant frire rôtir riz
        pain farine beurre fromage lait yaourt œufs poulet poisson soupe
        salade tomates oignons ail carottes pommes bananes sel sucre huile
        eau bouteille bocal réfrigérateur congélateur placard étagère récipient couvercle restes
        décongeler congelé frais mûr laver lavage linge lessive rincer sécher
        séchage serviette chemise chaussettes chaussures parapluie pluie pluvieux vent ensoleillé
        nuageux veste sac clés vélo pneu roue frein chaîne pompe
        pression voiture batterie jardin terre plante plantes pot graines feuilles
        fleurs arroser printemps été automne hiver saison marcher marche étirer
        exercice entraînement calendrier rendez-vous demain matin soir coucher dormir sommeil
        repos sieste nettoyer nettoyage balai serpillière poussière aspirateur vaisselle éponge
        savon poubelle ranger essuyer humide sec sortir promenade agenda fatigue
        """.split()
    ),
    "pt": frozenset(
        """
        cozinhar cozinhando cozido assar ferver fervendo fritar arroz pão farinha
        manteiga queijo leite iogurte ovos frango peixe sopa salada batatas
        tomates cebolas alho cenouras maçãs bananas sal açúcar óleo água
        garrafa pote geladeira frigorífico congelador despensa prateleira recipiente tampa sobras
        descongelar congelado fresco maduro lavar lavando roupa detergente enxaguar secar
        secando toalha camisa meias sapatos guarda-chuva chuva chuvoso vento ensolarado
        nublado casaco bolsa chaves bicicleta pneu roda freio travão corrente
        bomba pressão carro bateria jardim terra planta plantas vaso sementes
        folhas flores regar primavera verão outono inverno estação caminhar caminhando
        alongar exercício treino calendário compromisso amanhã manhã tarde noite dormir
        dormindo descanso cochilo limpar limpando vassoura esfregona poeira aspirador louça
        esponja sabão lixo arrumar enxugar úmido húmido seco passeio horário
        """.split()
    ),
    "de": frozenset(
        """
        kochen gekocht backen gebacken sieden braten rösten reis brot mehl
        butter käse milch joghurt eier huhn fisch suppe salat kartoffeln
        tomaten zwiebeln knoblauch karotten äpfel bananen salz zucker öl wasser
        flasche glas kühlschrank gefrierschrank vorrat regal behälter deckel reste auftauen
        gefroren frisch reif waschen wäsche waschmittel spülen trocknen trocken handtuch
        kleidung hemd socken schuhe regenschirm regen regnerisch wind windig sonnig
        bewölkt jacke tasche schlüssel fahrrad reifen rad bremse bremsen kette
        pumpe luftdruck auto batterie garten erde pflanze pflanzen topf samen
        blätter blumen gießen frühling sommer herbst winter jahreszeit gehen spazieren
        dehnen sport training kalender termin morgen morgens abends schlafenszeit schlafen
        schlaf ruhe nickerchen putzen reinigen besen mopp staub staubsauger geschirr
        schwamm seife müll aufräumen wischen feucht ausflug bewegung pause zeitplan
        """.split()
    ),
    "id": frozenset(
        """
        masak memasak matang panggang memanggang rebus merebus goreng menggoreng nasi
        beras roti tepung mentega keju susu yoghurt telur ayam ikan
        sup salad kentang tomat bawang wortel apel pisang garam gula
        minyak air botol stoples kulkas pembeku lemari rak wadah tutup
        sisa mencairkan beku segar ranum cuci mencuci cucian deterjen bilas
        membilas kering mengeringkan handuk pakaian kemeja kaus kaki sepatu payung
        hujan berangin cerah mendung jaket tas kunci sepeda ban roda
        rem rantai pompa tekanan mobil aki kebun tanah tanaman menanam
        pot benih daun bunga menyiram semi panas gugur dingin musim
        jalan berjalan peregangan olahraga latihan kalender janji besok pagi sore
        malam tidur istirahat lelap bersih membersihkan sapu mengepel debu penyedot
        piring spons sabun sampah merapikan lap lembap keluar santai jadwal
        """.split()
    ),
    "tr": frozenset(
        """
        yemek pişirmek pişmiş pişiyor kaynatmak kaynamak kızartmak fırın pirinç ekmek
        un tereyağı peynir süt yoğurt yumurta tavuk balık çorba salata
        patates domates soğan sarımsak havuç elma muz tuz şeker yağ
        su şişe kavanoz buzdolabı dondurucu kiler raf kap kapak artan
        çözülmek donmuş taze olgun yıkamak yıkıyor çamaşır deterjan durulamak kurutmak
        kuru havlu kıyafet gömlek çorap ayakkabı şemsiye yağmur yağmurlu rüzgar
        rüzgarlı güneşli bulutlu ceket çanta anahtar bisiklet lastik tekerlek fren
        zincir pompa basınç araba akü bahçe toprak bitki saksı tohum
        yaprak çiçek sulamak ilkbahar yaz sonbahar kış mevsim yürümek yürüyüş
        esnemek egzersiz antrenman takvim randevu yarın sabah akşam yatmak uyumak
        uyku dinlenmek şekerleme temizlemek temizlik süpürge paspas toz bulaşık sünger
        sabun çöp toplamak silmek nemli dışarı dinlenme program spor bakım
        """.split()
    ),
    "ru": frozenset(
        """
        готовить готовлю готовиться печь выпекать кипятить кипит жарить запекать рис
        хлеб мука масло сыр молоко йогурт яйца курица рыба суп
        салат картофель помидоры лук чеснок морковь яблоки бананы соль сахар
        вода бутылка банка холодильник морозилка кладовая полка контейнер крышка остатки
        разморозить замороженный свежий спелый мыть мою стирка бельё порошок полоскать
        сушить сухой полотенце одежда рубашка носки обувь зонт дождь дождливый
        ветер ветрено солнечно облачно куртка сумка ключи велосипед шина колесо
        тормоз цепь насос давление машина аккумулятор сад земля растение горшок
        семена листья цветы поливать весна лето осень зима сезон гулять
        прогулка растяжка упражнение тренировка календарь встреча завтра утро вечер спать
        сон отдых дремать уборка убирать веник швабра пыль пылесос посуда
        губка мыло мусор протирать влажный порядок расписание зарядка уход мытьё
        """.split()
    ),
    "hi": frozenset(
        """
        खाना पकाना पकाकर उबालना उबलता तलना भूनना सेंकना चावल रोटी
        आटा मक्खन पनीर दूध दही अंडे चिकन मछली सूप सलाद
        आलू टमाटर प्याज लहसुन गाजर सेब केले नमक चीनी तेल
        पानी बोतल जार फ्रिज फ्रीजर अलमारी शेल्फ डिब्बा ढक्कन बचा
        पिघलाना जमी ताजा पका धोना धोकर धुलाई कपड़े साबुन खंगालना
        सुखाना सूखा तौलिया कमीज मोजे जूते छाता बारिश बरसात हवा
        धूप बादल जैकेट थैला चाबी साइकिल टायर पहिया ब्रेक चेन
        पंप दबाव कार बैटरी बगीचा मिट्टी पौधा गमला बीज पत्ते
        फूल सींचना वसंत गर्मी पतझड़ सर्दी मौसम चलना टहलना खिंचाव
        व्यायाम कसरत कैलेंडर मुलाकात कल सुबह शाम सोना नींद आराम
        झपकी सफाई झाड़ू पोंछा धूल वैक्यूम बर्तन स्पंज कचरा पोंछना
        समेटना गीला बाहर सैर समय दिनचर्या थकान रखरखाव धोए जागना
        """.split()
    ),
    "mr": frozenset(
        """
        स्वयंपाक शिजवणे शिजलेले उकळणे उकळते तळणे भाजणे भात तांदूळ पोळी
        पीठ लोणी चीज दूध दही अंडी कोंबडी मासे सूप कोशिंबीर
        बटाटे टोमॅटो कांदे लसूण गाजर सफरचंद केळी मीठ साखर तेल
        पाणी बाटली बरणी फ्रिज फ्रीजर कपाट शेल्फ डबा झाकण उरलेले
        वितळवणे गोठलेले ताजे पिकलेले धुणे धुतलेले कपडे साबण विसळणे वाळवणे
        कोरडे टॉवेल सदरा मोजे बूट छत्री पाऊस पावसाळी वारा ऊन
        ढग जाकीट पिशवी चावी सायकल टायर चाक ब्रेक साखळी पंप
        दाब गाडी बॅटरी बाग माती रोप कुंडी बिया पाने फुले
        शिंपडणे वसंत उन्हाळा शरद हिवाळा ऋतू चालणे फिरणे ताणणे व्यायाम
        सराव दिनदर्शिका भेट उद्या सकाळ संध्याकाळ झोपणे झोप विश्रांती डुलकी
        स्वच्छता झाडू फडके धूळ भांडी स्पंज कचरा पुसणे आवरणे ओले
        बाहेर फेरफटका वेळापत्रक थकवा देखभाल धुलाई उठणे जेवण ठेवणे उन्हात
        """.split()
    ),
    "bn": frozenset(
        """
        রান্না রাঁধা সেদ্ধ ফুটানো ফুটছে ভাজা সেঁকা ভাত চাল রুটি
        আটা মাখন পনির দুধ দই ডিম মুরগি মাছ স্যুপ সালাদ
        আলু টমেটো পেঁয়াজ রসুন গাজর আপেল কলা লবণ চিনি তেল
        পানি জল বোতল বয়াম ফ্রিজ ফ্রিজার আলমারি তাক পাত্র ঢাকনা
        বেঁচে গলানো জমাট তাজা পাকা ধোয়া ধুয়ে কাপড় সাবান কাচা
        শুকানো শুকনো তোয়ালে জামা মোজা জুতো ছাতা বৃষ্টি বর্ষা বাতাস
        রোদ মেঘ জ্যাকেট ব্যাগ চাবি সাইকেল টায়ার চাকা ব্রেক চেন
        পাম্প চাপ গাড়ি ব্যাটারি বাগান মাটি গাছ টব বীজ পাতা
        ফুল সেচ বসন্ত গ্রীষ্ম শরৎ শীত ঋতু হাঁটা হাঁটছি টানা
        ব্যায়াম অনুশীলন ক্যালেন্ডার সাক্ষাৎ আগামীকাল সকাল সন্ধ্যা ঘুমানো ঘুম বিশ্রাম
        তন্দ্রা পরিষ্কার ঝাড়ু মোছা ধুলো বাসন স্পঞ্জ আবর্জনা মুছতে গোছানো
        ভেজা বাইরে বেড়ানো সময়সূচি ক্লান্তি যত্ন ধোওয়া জাগা দুপুর রাত
        """.split()
    ),
    "ur": frozenset(
        """
        کھانا پکانا پکا ابالنا ابلتا تلنا بھوننا سینکنا چاول روٹی
        آٹا مکھن پنیر دودھ دہی انڈے مرغی مچھلی سوپ سلاد
        آلو ٹماٹر پیاز لہسن گاجر سیب کیلے نمک چینی تیل
        پانی بوتل مرتبان فریج فریزر الماری شیلف ڈبہ ڈھکن بچا
        پگھلانا جما تازہ پکے دھونا دھوکر دھلائی کپڑے صابن کھنگالنا
        سکھانا خشک تولیہ قمیض موزے جوتے چھتری بارش برسات ہوا
        دھوپ بادل جیکٹ تھیلا چابی سائیکل ٹائر پہیہ بریک زنجیر
        پمپ دباؤ گاڑی بیٹری باغ مٹی پودا گملا بیج پتے
        پھول سینچنا بہار گرمی خزاں سردی موسم چلنا ٹہلنا کھینچنا
        ورزش مشق کیلنڈر ملاقات کل صبح شام سونا نیند آرام
        جھپکی صفائی جھاڑو پونچھا دھول برتن سپنج کوڑا پونچھنا سمیٹنا
        گیلا باہر سیر وقت معمول تھکن نگہداشت دھوئے جاگنا دوپہر
        """.split()
    ),
    "te": frozenset(
        """
        వంట వండటం వండిన ఉడికించడం ఉడికిన వేయించడం కాల్చడం అన్నం బియ్యం రొట్టె
        పిండి వెన్న జున్ను పాలు పెరుగు గుడ్లు చికెన్ చేప సూప్ సలాడ్
        బంగాళాదుంప టమాటా ఉల్లిపాయ వెల్లుల్లి క్యారెట్ ఆపిల్ అరటిపండు ఉప్పు చక్కెర నూనె
        నీరు సీసా జాడీ ఫ్రిజ్ ఫ్రీజర్ అలమారి అర డబ్బా మూత మిగిలిన
        కరిగించడం గడ్డకట్టిన తాజా పండిన కడగడం కడిగిన ఉతకడం బట్టలు సబ్బు కడుగుతూ
        ఆరబెట్టడం పొడి తువాలు చొక్కా సాక్సులు బూట్లు గొడుగు వర్షం వాన గాలి
        ఎండ మేఘాలు జాకెట్ సంచి తాళం సైకిల్ టైరు చక్రం బ్రేక్ గొలుసు
        పంపు ఒత్తిడి కారు బ్యాటరీ తోట మట్టి మొక్క కుండ విత్తనాలు ఆకులు
        పూలు నీరుపోయడం వసంతం వేసవి శరదృతువు చలికాలం ఋతువు నడవడం నడక సాగదీయడం
        వ్యాయామం సాధన క్యాలెండర్ సమావేశం రేపు ఉదయం సాయంత్రం నిద్రపోవడం నిద్ర విశ్రాంతి
        కునుకు శుభ్రం చీపురు తుడవడం దుమ్ము పాత్రలు స్పాంజ్ చెత్త తుడిచిన సర్దడం
        తడి బయట విహారం సమయపట్టిక అలసట సంరక్షణ ఉతికిన మేల్కొనడం మధ్యాహ్నం రాత్రి
        """.split()
    ),
    "ar": frozenset(
        """
        طبخ يطبخ مطبوخ خبز يخبز غلي يغلي قلي يشوي أرز
        دقيق زبدة جبن حليب زبادي بيض دجاج سمك حساء سلطة
        بطاطس طماطم بصل ثوم جزر تفاح موز ملح سكر زيت
        ماء زجاجة مرطبان ثلاجة مجمد خزانة رف وعاء غطاء بقايا
        إذابة مجمدة طازج ناضج غسل يغسل غسيل ملابس منظف شطف
        تجفيف جاف منشفة قميص جوارب أحذية مظلة مطر ممطر رياح
        مشمس غائم سترة حقيبة مفاتيح دراجة إطار عجلة فرامل سلسلة
        مضخة ضغط سيارة بطارية حديقة تربة نبات أصيص بذور أوراق
        زهور سقي ربيع صيف خريف شتاء موسم مشي يمشي تمدد
        رياضة تمرين تقويم موعد غدا صباح مساء نوم ينام راحة
        قيلولة تنظيف ينظف مكنسة ممسحة غبار أطباق إسفنجة صابون قمامة
        ترتيب مسح رطب خروج نزهة جدول تعب صيانة استيقاظ ظهيرة
        """.split()
    ),
    "zh": frozenset(
        """
        做饭 煮饭 煮熟 烘烤 烧开 沸腾 煎 炒 烤 米饭
        大米 面包 面粉 黄油 奶酪 牛奶 酸奶 鸡蛋 鸡肉 鱼
        汤 沙拉 土豆 西红柿 洋葱 大蒜 胡萝卜 苹果 香蕉 盐
        糖 油 水 瓶子 罐子 冰箱 冷冻室 橱柜 架子 容器
        盖子 剩菜 解冻 冷冻 新鲜 成熟 清洗 洗衣 洗衣液 漂洗
        晾干 毛巾 衣服 衬衫 袜子 鞋子 雨伞 下雨 雨天 刮风
        晴天 阴天 外套 包 钥匙 自行车 轮胎 车轮 刹车 链条
        打气筒 气压 汽车 电池 花园 泥土 植物 花盆 种子 叶子
        花 浇水 春天 夏天 秋天 冬天 季节 走路 散步 拉伸
        运动 锻炼 日历 预约 明天 早上 晚上 就寝 睡觉 睡眠
        休息 午睡 打扫 扫帚 拖把 灰尘 吸尘器 餐具 海绵 肥皂
        垃圾 整理 擦拭 潮湿 干燥 出门 郊游 日程 疲劳 保养
        """.split()
    ),
    "ja": frozenset(
        """
        料理 調理 煮る 煮込む 茹でる 沸かす 炒める 揚げる 焼く ご飯
        米 パン 小麦粉 バター チーズ 牛乳 ヨーグルト 卵 鶏肉 魚
        スープ サラダ じゃがいも トマト 玉ねぎ にんにく にんじん りんご バナナ 塩
        砂糖 油 水 瓶 保存容器 冷蔵庫 冷凍庫 食器棚 棚 容器
        蓋 残り物 解凍 冷凍 新鮮 熟した 洗う 洗濯 洗濯物 洗剤
        すすぐ 干す 乾かす タオル 服 シャツ 靴下 靴 傘 雨
        雨降り 風 晴れ 曇り 上着 鞄 鍵 自転車 タイヤ 車輪
        ブレーキ チェーン 空気入れ 空気圧 自動車 バッテリー 庭 土 植物 植木鉢
        種 葉 花 水やり 春 夏 秋 冬 季節 歩く
        散歩 伸ばす 運動 筋トレ カレンダー 予定 明日 朝 夕方 寝る
        睡眠 休憩 昼寝 掃除 ほうき 雑巾 ほこり 掃除機 食器 スポンジ
        石鹸 ごみ 片付ける 拭く 湿った 乾いた 外出 日程 疲れ 手入れ
        """.split()
    ),
}
