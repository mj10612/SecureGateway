"""Independently authored lexical support for ordinary workflow instructions.

These deliberately incomplete word lists were written from general linguistic
knowledge without consulting fixtures, existing vocabulary, or repository code.
Whitespace separates individual surface forms, including the parts of naturally
spaced compound verbs. Entries are lowercase where applicable and NFC-normalized.
They describe actions and relationships, rather than identities or subject areas.
"""

WORKFLOW_OPERATIONS: dict[str, frozenset[str]] = {
    "en": frozenset(
        """
        align aligned annotate annotated avoid book booked bought buy check checked checking checks
        contact contacted depend depends draft drafted drafting drafts fill filled filter filtered
        flag flagged flags identified identify invent invented keep keeping keeps kept list listed
        listing lists mark marked marks match matched modified modify notified notify omit order
        ordered post posted prepare prepared prepares preparing present presented presenting
        presents preserve purchase purchased register registered replace replaced request reserve
        reserved retain reuse reused schedule scheduled select selected send sending sends sent
        show showed showing shown shows submit upload uploaded write writes writing written wrote
        """.split()
    ),
    "ko": frozenset(
        """
        걸러 걸러내 게시 게시해 교체 교체해 구매 구매해 나열 나열하세요 나열해 남겨 달아 대조 대조해 등록 등록해 만들어 말고 맞춰 바꿔 보내 보내세요 보내줘 보내지
        보여 보여주세요 보여주지 보여줘 선택 선택하세요 선택하지 선택해 수정 수정하세요 수정하지 수정해 식별 식별해 써 쓰세요 쓰지 알려 알려줘 업로드 업로드해 연락
        연락하세요 연락하지 연락해 예약 예약해 유지 유지하세요 유지해 의존 의존해 일치시켜 작성 작성하고 작성하세요 작성하지 작성해 잡아 재사용 재사용해 정렬 정렬하세요
        정렬해 제시 제시하세요 제시해 주문 주문해 주석 주석달아 준비 준비하고 준비하세요 준비하지 준비해 채우고 채우세요 채우지 채워 초안 통보 통지 표시 표시하세요
        표시하지 표시해 필터링 필터링해 확인 확인하고 확인하세요 확인하지 확인해
        """.split()
    ),
    "es": frozenset(
        """
        alinear alinee anotar anote avisar avise coincidir comparar compare compra comprar compre
        comprobar compruebe conservar conserve contacta contactar contacte dependa depende depender
        enumerar enviar envía envíe escriba escribe escribir filtrar filtre identificar identifique
        inventa inventar invente lista listar liste mantener mantenga mantén marcar marque modifica
        modificar modifique mostrar muestra muestre notificar notifique ordena ordenar ordene
        prepara preparar prepare presenta presentar presente programa programar programe publica
        publicar publique redacta redactar redacte reemplace reemplaza reemplazar registra
        registrar registre rellena rellenar rellene reserva reservar reserve reutilice reutiliza
        reutilizar selecciona seleccionar seleccione señalar señale suba sube subir verificar
        verifique
        """.split()
    ),
    "fr": frozenset(
        """
        acheter achetez achète aligner alignez annoter annotez avertir avertis avertissez charge
        charger chargez commande commander commandez comparer comparez conserver conservez contacte
        contacter contactez contrôler contrôlez correspondre dépend dépende dépendre enregistrer
        enregistrez envoie envoyer envoyez filtrer filtrez garder gardez identifier identifiez
        inscrire inscris inscrivez invente inventer inventez liste lister listez marquer marquez
        modifie modifier modifiez montrer montrez notifie notifier notifiez ordonne ordonner
        ordonnez planifie planifier planifiez prépare préparer préparez présenter présentez publie
        publier publiez remplace remplacer remplacez remplir remplis remplissez rédige rédiger
        rédigez réserve réserver réservez réutilise réutiliser réutilisez signaler signalez
        sélectionner sélectionnez vérifie vérifier vérifiez écrire écris écrivez énumérer
        """.split()
    ),
    "pt": frozenset(
        """
        agenda agendar agende alinhar alinhe anotar anote apresentar apresente avisa avisar avise
        carrega carregar carregue comparar compare compra comprar compre conferir confira conservar
        conserve contactar contatar contate corresponder dependa depende depender encomenda
        encomendar encomende enumerar envia enviar envie escreva escreve escrever filtrar filtre
        identificar identifique inventa inventar invente lista listar liste mantenha manter mantém
        marcar marque modifica modificar modifique mostra mostrar mostre notifica notificar
        notifique ordena ordenar ordene preencha preenche preencher prepara preparar prepare
        publica publicar publique redige redigir redija registra registrar registre reserva
        reservar reserve reutiliza reutilizar reutilize seleciona selecionar selecione sinalizar
        sinalize substitua substitui substituir verificar verifique
        """.split()
    ),
    "de": frozenset(
        """
        abgleichen abhänge abhängen angleichen anmelden annotieren anordnen auflisten ausfüllen
        ausrichten auswählen behalte behalten beibehalten benachrichtige benachrichtigen bereite
        bestelle bestellen buche buchen entwerfen entwirf erfinde erfinden erfunden ergänze
        ergänzen erkenne erkennen ersetze ersetzen filtere filtern fülle geändert gleiche hochladen
        hängt identifizieren informiere informieren kaufe kaufen keinesfalls kennzeichne
        kennzeichnen kommentiere kommentieren kontaktiere kontaktieren lade liste markiere
        markieren markiert melde modifiziere modifizieren nicht ordne ordnen plane planen poste
        posten präsentiere prüfen registriere registrieren reserviere reservieren richte schicke
        schicken schreibe schreiben schreibt sende senden sortiere sortieren terminieren
        vergleichen verwende veröffentliche veröffentlichen vorbereiten wiederverwende
        wiederverwenden wähle zeige zeigen zeigt ändere ändern übereinstimmen überprüfen
        """.split()
    ),
    "id": frozenset(
        """
        anotasi atur beli bergantung beritahu beritahukan cadangkan cek ciptakan daftar daftarkan
        filter ganti gantikan gunakan hubungi identifikasi isi isikan jadwalkan jangan kabari
        karang kirim kirimkan membeli memberitahu memeriksa memesan memilih memodifikasi
        mempertahankan memposting mempublikasikan menampilkan menandai mencadangkan menciptakan
        mencocokkan mendaftar menerbitkan mengabari mengarang mengatur mengganti menggunakan
        menghubungi mengidentifikasi mengirim mengirimkan mengisi mengubah mengunggah mengurutkan
        menjadwalkan menulis menunjukkan menyajikan menyaring menyelaraskan menyesuaikan menyiapkan
        menyimpan menyunting menyusun modifikasi pakai periksa persiapkan pertahankan pesan pilih
        posting publikasikan reservasi rincikan sajikan saring selaraskan sesuaikan siapkan simpan
        sunting susun tampilkan tandai terbitkan tergantung tulis tuliskan tunjukkan ubah ulangi
        unggah urutkan
        """.split()
    ),
    "tr": frozenset(
        """
        al alma alın ayır ayırın açıkla belirt belirtin bildir bildirin denetle denetleyin değiştir
        değiştirin değiştirme doldur doldurmayın doldurun doğrula doğrulayın düzenle düzenleyin
        edin ekle ekleyin eşleştir eşleştirerek eşleştirin filtrele filtreleyin geçin gönder
        gönderin gönderme göster gösterin gösterme hazırla hazırlayarak hazırlayın hizala hizalayın
        iletişim iletişime işaretle işaretleme işaretleyin kaydedin kaydet kontrol koru koruyun koy
        koyun kullan kullanarak kullanma kullanın listele listeleyerek listeleyin oluştur oluşturun
        paylaş paylaşın planla planlayın rezerve sakla seç seçerek seçin seçme sipariş sun sunarak
        sunun süz süzün sırala sıralayarak sıralayın tanımla taslak uydur uydurmayın ver verin
        yayımla yayımlayın yaz yazarak yazma yazın yükle yükleme yükleyin
        """.split()
    ),
    "ru": frozenset(
        """
        аннотировать аннотируйте выбери выберите выбрать выровняйте выровнять выявите выявить
        забронировать забронируй забронируйте зависеть загрузи загрузите загрузить закажи закажите
        заказать замени замените заменить запланировать запланируй запланируйте заполни заполните
        заполнить зарегистрировать зарегистрируй зарегистрируйте измени измените изменить
        использовать используйте купи купите купить написать напиши напишите определи определите
        определить опубликовать опубликуйте оставить оставь оставьте отметить отметь отметьте
        отправить отправь отправьте отфильтровать отфильтруйте перечисли перечислите перечислить
        подготовив подготовить подготовь подготовьте покажи покажите показать пометить пометь
        пометьте представить представь представьте придумай придумать придумывайте проверить
        проверь проверьте свяжитесь связаться сообщи сообщите сообщить сопоставить сопоставь
        сопоставьте составить составь составьте сохрани сохраните сохранить уведомите уведомить
        упорядочить упорядочьте
        """.split()
    ),
    "hi": frozenset(
        """
        अपलोड आरक्षित उपयोग करके करना करें कीजिए क्रमबद्ध खरीदना खरीदें गढ़ना गढ़ें चिन्हित चिह्नित
        चुनकर चुनना चुनिए चुनें चुनो छाँटकर छाँटें छांटें जाँचकर जाँचना जाँचें जांचें जोड़ना जोड़ें
        टिप्पणी तैयार दर्ज दिखाइए दिखाएँ दिखाएं दोहराएँ दोहराएं निर्धारित निर्भर पंजीकृत पहचानना
        पहचानिए पहचानें पुनः पेश पोस्ट प्रकाशित प्रस्तुत बचाएँ बचाएं बताइए बताएँ बताएं बदलकर बदलना
        बदलवाएं बदलिए बदलें बनाएँ बनाएं बुक भरकर भरना भरिए भरें भेजकर भेजना भेजिए भेजें भेजो मँगाएँ
        मंगाएं मत मसौदा मिलाएँ मिलाएं मिलाकर मिलान मिलाना रखकर रखना रखिए रखें रखो लगाएँ लगाएं लिखकर
        लिखना लिखिए लिखें लिखो संपर्क संरेखित संशोधित सजाएँ सजाएं सूचित सूचीबद्ध
        """.split()
    ),
    "mr": frozenset(
        """
        अदलाबदल अपलोड अवलंबून आरक्षित ओळखणे ओळखा ओळखून करणे करा करावे करावेत करू करून कळवा कळवावे
        क्रम खरेदी खूण गाळा गाळून चिन्हांकित जपा जुळवणे जुळवा जुळवावे जुळवून जोडणे जोडा जोडून टिपा
        टिप्पणी ठरवा ठरवून ठेवणे ठेवा ठेवावे ठेवून तपासणे तपासा तपासावे तपासून तयार दाखवणे दाखवा
        दाखवावे दाखवून नका नियोजित निवडणे निवडा निवडून नोंद नोंदणी नोंदवणे नोंदवा नोंदवावे नोंदवून
        पाठवणे पाठवा पाठवावे पाठवून पुन्हा प्रकाशित बदलणे बदला बदलावे बदलून बनवा बनवून बुक भरणे भरा
        भरावे भरून मसुदा मांडा मांडावे मागवा मोजून यादी यादीबद्ध रचा रचू राखा लावा लिहा लिहावे
        लिहिणे लिहून वापरणे वापरा वापरून संपर्क संरेखित सादर सुधारणा सुधारा
        """.split()
    ),
    "bn": frozenset(
        """
        অবহিত অর্ডার আপলোড উদ্ভাবন উপস্থাপন করবেন করা করুক করুন করে করো কিনুন কিনে কেনা ক্রমানুসারে
        খসড়া চিনুন চিহ্ন চিহ্নিত চেনা ছাঁকুন ছাঁকো ছেঁকে জানাও জানান জানিয়ে টীকা তালিকা
        তালিকাভুক্ত তৈরি দেখাও দেখান দেখানো দেখিয়ে নথিভুক্ত না নিবন্ধন নির্ধারণ নির্বাচন নির্ভর
        পরিবর্তন পরীক্ষা পাঠাও পাঠান পাঠানো পাঠিয়ে পুনর্ব্যবহার পূরণ পেশ পোস্ট প্রকাশ প্রতিস্থাপন
        প্রস্তুত ফিল্টার বজায় বদলাও বদলান বদলে বাছাই বাছুন বানান বানিয়ে বুক বেছে ব্যবহার ভরুন ভরে
        মন্তব্য মিলিয়ে মেলাও মেলান মেলানো যাচাই যোগ যোগাযোগ রাখা রাখুন রাখো রেখে লিখবেন লিখুন লিখে
        লিখো লেখা লেখো শনাক্ত সংরক্ষণ সংশোধন সময়সূচি সাজাও সাজান সাজানো সাজিয়ে সারিবদ্ধ
        """.split()
    ),
    "ur": frozenset(
        """
        آہنگ استعمال اطلاع انحصار اندراج اپ ایجاد بتاؤ بتائیں بتانا بدلنا بدلو بدلیں برقرار بناؤ
        بنائیں بنانا بک بھرنا بھریں بھیجنا بھیجو بھیجیں تبدیل تبصرہ ترتیب ترمیم تصدیق تیار جانچنا
        جانچیں جوڑیں خریدنا خریدو خریدیں درج دوبارہ دکھاؤ دکھائیں دکھائیے دکھانا رابطہ رجسٹر رکھنا
        رکھو رکھیں ریزرو سیدھا شائع شامل شناخت طے فلٹر فہرست لوڈ لکھنا لکھو لکھیں لگاؤ لگائیں لگانا
        مت متبادل محفوظ مرتب مسودہ مقرر ملاؤ ملائیں ملانا منتخب منگوائیں موازنہ نشان نشانزد پوسٹ
        پُر پہچاننا پہچانو پہچانیں پیش چننا چنو چنیں چھانٹنا چھانٹو چھانٹیں کرنا کرو کریں کیجئے
        کیجیے گھڑنا گھڑیں ہم
        """.split()
    ),
    "te": frozenset(
        """
        అప్లోడ్ అమర్చండి అమర్చి ఆధారపడి ఆధారపడుతుంది ఆర్డర్ ఉంచండి ఉంచవద్దు ఉంచాలి ఉంచి ఎంచుకుని
        ఎంచుకోండి ఎంచుకోవద్దు కల్పించండి కొనండి కొనవద్దు కొనసాగించండి కొని క్రమబద్ధీకరించండి
        క్రమబద్ధీకరించి గుర్తించండి గుర్తించి గుర్తుపెట్టండి గుర్తుపెట్టి చూపండి చూపవద్దు చూపించండి
        చూపించి చేయండి చేయకండి చేయడం చేయవద్దు చేయాలి చేసి జాబితా జాబితాచేయండి జోడించండి జోడించి
        తనిఖీ తనిఖీచేయండి తయారు తయారుచేయండి తయారుచేసి తెలియజేయండి తెలియజేసి నమోదు నమోదుచేయండి
        నింపండి నింపవద్దు నింపి నిర్ధారించండి పంపండి పంపవద్దు పంపి పరిశీలించండి పరిశీలించి
        పునర్వినియోగించండి పూరించండి పూరించి ప్రచురించండి ప్రచురించి ప్రదర్శించండి ఫిల్టర్ బుక్
        భద్రపరచండి భద్రపరచి భర్తీచేయండి మళ్లీ మార్చండి మార్చవద్దు మార్చాలి మార్చి ముసాయిదా రాయండి
        రాయవద్దు రాయాలి రాసి రాస్తూ రిజర్వ్ వడపోయండి వడపోసి వాడండి వాడి వ్యాఖ్యానించండి వ్రాయండి
        షెడ్యూల్ సంప్రదించండి సంప్రదించవద్దు సంప్రదించి సమర్పించండి సమర్పించి సరిపోల్చండి సరిపోల్చి
        సవరించండి సవరించి సిద్ధం సిద్ధంచేయండి సిద్ధంచేయాలి సిద్ధంచేసి
        """.split()
    ),
    "ar": frozenset(
        """
        أبق أبقوا أبلغ أبلغوا أخطر أخطروا أدرج أدرجوا أرسل أرسلوا أشر أشيروا أعد أعدوا إخطار إدراج
        إرسال اتصل اتصلوا احتفظ احتفظوا احجز احجزوا احفظ اختاروا اختر اخترع ارفع ارفعوا استبدل
        استبدلوا استخدام استخدم استخدموا اسرد اسردوا اشتر اشتروا اطلب اطلبوا اعرض اعرضوا افحص
        افحصوا اكتب اكتبوا املأ املؤوا انشر انشروا تحديد تحقق تحققوا ترتيب تسجيل تعتمد تعديل تعليق
        تقديم تواصل تواصلوا جدول جدولة جهز جهزوا حاذ حجز حدد حددوا حضر حضروا رتب رتبوا رشح رشحوا
        رفع سجل سجلوا صغ صف طابق طابقوا عدل عدلوا عرض علق علقوا علم علموا قارن قارنوا قدم قدموا
        كتابة مطابقة ملء نشر يعتمد
        """.split()
    ),
    "zh": frozenset(
        """
        上传 上傳 下单 下單 依賴 依赖 保持 保留 修改 写出 准备 列举 列出 列舉 匹配 发布 发帖 发送 取决于 取決於 呈现 呈現 告知 填写 填寫 复用 安排 寄送 寫出 对照
        对齐 對照 對齊 展示 復用 找出 排列 排序 撰写 撰寫 显示 更改 替换 替換 标注 标记 核对 核對 检查 標記 標註 檢查 比对 比對 注册 注释 準備 登記 登记 發布
        發帖 發送 筛选 篩選 編造 编造 罗列 羅列 联系 联络 聯絡 聯繫 訂購 註冊 註釋 調整 識別 订购 识别 调整 購買 购买 起草 过滤 选择 通知 過濾 選擇 重用 預約
        預訂 顯示 预约 预订
        """.split()
    ),
    "ja": frozenset(
        """
        アップロード フィルター マーク マークして 一致 一致する 下書き 下書きして 並べて 並べる 並べ替え 予定 予約 依存 依存する 保持 保持して 修正 修正して 公開 再利用
        再利用して 列挙 列挙して 創作 印を付けて 埋めて 変えず 変更 変更して 投稿 抽出 抽出して 捏造 揃えて 揃える 提示 提示して 整列 書いて 書かず 書かない 書き
        書きます 書く 検査 検証 残さず 残して 残す 注文 注記 注記して 注釈 注釈して 準備 準備して 準備する 照合 照合して 特定 特定して 用意 用意して 登録 登録して 確認
        確認し 確認して 示し 示して 示す 絞って 絞る 置き換えて 置換 表示 表示して 記入 記載 記載して 識別 識別して 購入 起草 起草して 送って 送らない 送る 送信
        送信して 通知 通知して 連絡 連絡して 連絡しない 選ぶ 選んで 選択 選択して
        """.split()
    ),
}

WORKFLOW_RELATIONS: dict[str, frozenset[str]] = {
    "en": frozenset(
        """
        after all ambiguous any appearance approval approved available before blank both condition
        conditional current different each either empty every exact exactly except existing
        explicit first following identical if individually mandatory marked missing neither never
        no none not only optional order original otherwise pending preceding precisely prior
        priority provided required respectively same sequence shared solely source sources
        subsequent supplied then together unapproved unavailable unchanged unclear unless until
        within without
        """.split()
    ),
    "ko": frozenset(
        """
        가능하면 가능한 각 각각 같은 공동 공유 공유된 공통 그대로 까지 내에서 누락 누락된 다 다른 단지 동일 동일한 둘 등장 만 모두 모호한 미승인 변경없이 불가능
        불명확 비어 빈 빠진 사용가능 선택사항 선택적 순서 순으로 승인 승인된 아니면 않으면 없는 없으면 없이 에서 오직 우선 우선순위 원본 이내 이전 이후 있는 있으면
        전에 정확 정확한 정확히 제외 조건 조건부 처음 첫 출처 표시된 필수 필요하면 필요한 후에
        """.split()
    ),
    "es": frozenset(
        """
        ambas ambigua ambiguo ambos antes aparición aprobación aprobada aprobado blanco cada
        compartida compartidas compartido compartidos condiciones condición dentro después
        diferente diferentes disponible disponibles entonces exacta exactamente exacto excepto
        faltante faltantes fuente fuentes inalterado incierto indisponible indisponibles intacto
        marcada marcado mientras misma mismo mismos necesaria necesario ni ninguna ninguno no
        obligatoria opcional opcionales orden original originales pendiente primera primero
        prioridad salvo si sin sola solamente solo vacía vacío vacíos únicamente
        """.split()
    ),
    "fr": frozenset(
        """
        alors ambigu ambiguë apparition approbation approuvé approuvée après aucun aucune avant
        blanc blanche chacun chacune condition conditions dans deux différent différente disponible
        disponibles ensemble exact exacte exactement facultatif facultative flou floue identique
        inchangé inchangée indisponible indisponibles jusqu'à lorsque manquant manquante marqué
        marquée même mêmes ni obligatoire ordre original originale partagé partagée partagées
        partagés premier première priorité requis requise sans sauf seul seule seulement si source
        sources uniquement vide vides
        """.split()
    ),
    "pt": frozenset(
        """
        ambas ambos ambígua ambíguo antes aparição apenas aprovada aprovado aprovação ausente
        ausentes branca branco cada compartilhada compartilhado condição condições dentro depois
        diferente diferentes disponíveis disponível enquanto então exata exatamente exato exceto
        exigida exigido faltante fonte fontes inalterada inalterado incerta incerto indisponível
        marcada marcado mesma mesmas mesmo mesmos necessária necessário nem nenhum nenhuma
        obrigatória obrigatório opcionais opcional ordem originais original primeira primeiro
        prioridade salvo se sem somente só vazia vazio
        """.split()
    ),
    "de": frozenset(
        """
        auftreten ausschließlich außer bedingung bedingungen beide beiden benötigt danach dann
        erforderlich erforderliche erste ersten exakt falls fehlend fehlende fehlenden freigabe
        gemeinsam genau genaue genehmigt genehmigung geteilt geteilte gleich gleiche gleichen
        identisch innerhalb jede jeder jedes jeweils leer leere leeren markiert markierte
        mehrdeutig nach noch notwendige nur ohne optional optionale original priorität quelle
        quellen reihenfolge sofern unklar unklare unterschiedlich unverfügbar unverändert
        ursprüngliche verfügbar verfügbare verfügbaren verschiedene vor vorher weder wenn
        """.split()
    ),
    "id": frozenset(
        """
        ambigu antara apabila asal asli atau belum berbeda berikutnya bersama bersyarat bertanda
        berubah bila bukan dalam dan di dibagikan diperlukan disetujui ditandai hampa hanya harus
        hilang hingga identik jelas jika kecuali kedua keduanya kemunculan kondisi kosong kurang
        maka masing-masing maupun menunggu opsional persetujuan persis pertama pilihan prioritas
        pun saja sama sampai sebelum sebelumnya semata semula sesuai sesudah setelah setiap sumber
        syarat tanpa tepat tersedia tetap tiap tidak urutan wajib
        """.split()
    ),
    "tr": frozenset(
        """
        aynen aynı açık bağlı bekleyen belirsiz biri boş değişmeden değişmemiş dışında eksik eğer
        farklı gereken gerekli görünüm her hiçbir hiçbiri iki ikisi ikisini ikisinin ilk ise isteğe
        içerisinde için içinde işaretlenmiş işaretli kadar kaynak kaynakta kaynağı kesin koşul
        koşula koşullu kullanılabilir kullanılamayan mevcut olmadan olmadıkça olmayan onay onaylı
        onaysız onayı orijinal ortak paylaşılan sadece sonra sonrasında sıra sırası sırayla tam
        yalnız yalnızca zorunlu önce öncelik öncelikli öncesinde özgün şart
        """.split()
    ),
    "ru": frozenset(
        """
        без внутри до доступная доступные доступный другие другой если же иначе источник источника
        исходные исходный каждая каждое каждый лишь недоступные недоступный неизменный неизменными
        необязательные необязательный неоднозначный неясная неясный ни оба обе обоих общая общие
        общий обязательные обязательный одинаковые одинаковый одобрение одобрено оригинал
        отмеченные отмеченный отсутствует отсутствуют отсутствующий первое перед порядке порядок
        после появление появления приоритет пустая пустой пустые согласование та те только тот
        точная точно точный требуется требуются условие
        """.split()
    ),
    "hi": frozenset(
        """
        अंदर अगर अनिवार्य अनिश्चित अनुपलब्ध अनुपस्थित अनुमोदन अनुसार अन्यथा अपरिवर्तित अलग अस्पष्ट
        अस्वीकृत आवश्यक उपलब्ध उपस्थिति और केवल को कोई क्रम क्रमानुसार खाली गायब चिन्हित चिह्नित जब
        ठीक तक तो दोनों न पर पश्चात पहला पहली पहले पूर्व प्रत्येक प्राथमिकता बगैर बाद बिना भिन्न
        भीतर मात्र मूल में यथावत यदि या रिक्त लंबित लापता वही वैकल्पिक शर्त शर्तों सटीक समान सशर्त
        साझा सिर्फ सिर्फ़ से स्रोत स्वीकृत स्वीकृति हर ही
        """.split()
    ),
    "mr": frozenset(
        """
        अचूक अट अटी अनिवार्य अनुपलब्ध अपरिवर्तित अमंजूर असलेले असल्यास अस्पष्ट आणि आत आधी आवश्यक
        उपलब्ध उल्लेख ऐच्छिक किंवा केवळ कोणतेही क्रम क्रमाने गहाळ चिन्हांकित जोपर्यंत तंतोतंत तर
        तशीच तसाच तसेच तीच तेच तोच दोन्ही दोन्हीही नंतर नसले नसलेले नसल्यास नाही नाहीत नोंदवलेले
        पर्यायी पहिल्या पूर्वी प्रत्येक प्रत्येकी प्रथम प्राधान्य फक्त भिन्न मंजुरी मंजूर मध्ये
        मात्र मान्यता मूळ रिकामी रिकामे रिक्त विना वेगळी वेगळे शिवाय संदिग्ध समान सशर्त सामायिक
        स्रोत
        """.split()
    ),
    "bn": frozenset(
        """
        অগ্রাধিকার অথবা অননুমোদিত অনিশ্চিত অনুপলব্ধ অনুপস্থিত অনুমতি অনুমোদন অনুমোদিত অনুযায়ী
        অপরিবর্তিত অস্পষ্ট আগে আবশ্যক আলাদা আসল উপলব্ধ উপস্থিতি উভয় উভয়ই উল্লেখ উৎস একই এবং
        ঐচ্ছিক কেবল কোনোটিই ক্রম ক্রমানুসারে ক্রমে খালি চিহ্নিত ছাড়া দুটিই দুটো নয় না নাহলে
        পরবর্তী পরে পর্যন্ত পাওয়া পূর্বে প্রতি প্রতিটি প্রত্যেক প্রথম প্রথমে প্রয়োজনীয় ফাঁকা বাদ
        বাধ্যতামূলক ব্যতীত ভাগাভাগি ভিন্ন ভেতরে মধ্যে মাত্র মূল যথাযথ যদি যৌথ শর্ত শর্তসাপেক্ষ শুধু
        শূন্য সঠিক সমান হুবহু
        """.split()
    ),
    "ur": frozenset(
        """
        اجازت اختیاری اصل الا الگ اندر اور اگر بالکل برقرار بعد بغیر بھی ترتیب ترجیح ترجیحی تو تک
        خالی درست دستیاب دستیابی دونوں ذریعہ زیرالتوا سوا سے شدہ شرائط شرط صرف ضروری ضمن ظہور عین
        غائب غیر غیرواضح فقط قبل لازم لازمی ماخذ مبہم محض مختلف مشترک مشترکہ مشروط مطابق مطلوب
        منظور منظوری نامنظور ناموجود نشانزد نشانزدہ نہ نہیں واضح ورنہ وہی پہلا پہلی پہلے کوئی ہر یا
        یکساں
        """.split()
    ),
    "te": frozenset(
        """
        అందుబాటులో అదే అనుమతి అనుమతించిన అయితే అవసరమైన అసలు అస్పష్ట అస్పష్టమైన ఆమోదం ఆమోదించిన ఉంటే
        ఉన్న ఉమ్మడి ఏదీ ఐచ్ఛిక ఒక్కొక్క కనిపించని కనిపించిన కాదు కేవలం క్రమం క్రమంలో క్రమానుసారం
        ఖచ్చితంగా ఖచ్చితమైన ఖాళీ ఖాళీగా గుర్తించబడిన గుర్తించిన తప్ప తప్పనిసరి తప్పిపోయిన తరువాత
        తర్వాత తొలి పంచుకున్న ప్రకారం ప్రతి ప్రస్తావన ప్రాధాన్యత భాగస్వామ్య భిన్నమైన మరియు మాత్రమే
        మారకుండా ముందు మూల మూలం మొదటి యథాతథంగా రెండింటినీ రెండు రెండూ లభించని లభ్యమైన లేకపోతే
        లేకుండా లేని లేనిదే లోపల లోపు వేరు వేరైన షరతు షరతులతో సందిగ్ధమైన సమానమైన సరిగ్గా
        """.split()
    ),
    "ar": frozenset(
        """
        أصلي أول أولوية إلا إلزامي إلزامية اختياري اختيارية الأصل الأولى الترتيب المتاح المصدر بدون
        بعد ترتيب تغيير تماما حصرا خال خالية داخل دقيق دقيقة دون شرط ضمن ظهور غامض غير فارغ فارغة
        فقط قبل كل كلا كلتا كليهما لا لكل مبهم مبهمة متاح متاحة متوفر متوفرة محدد مختلف مختلفة
        مشترك مشتركة مشروط مصدر مطابق مطابقة مطلوب مطلوبة معتمد معلّم مفقود مفقودة موافق موافقة
        ناقص ناقصة نفس نفسه نفسها ولا
        """.split()
    ),
    "zh": frozenset(
        """
        一样 一樣 不变 不可用 不同 不明确 不明確 不清楚 不變 两者 之前 之后 之後 仅 仅限 优先 來源 僅 僅限 優先 兩者 共享 共同 共用 准确 出现 出現 原始 原文 只
        只有 可用 可选 可選 各 均不 完全 审批 審批 已标记 已標記 必需 必須 必须 批准 条件 来源 條件 模糊 每个 每個 沒有 没有 準確 相同 空白 精确 精確 缺失 缺少
        遗漏 遺漏 都不 除非 需要 順序 顺序 首次
        """.split()
    ),
    "ja": frozenset(
        """
        そのまま それぞれ だけ どちらも どちらもない なく なし により のみ まで マーク済み 不明 不明確 不足 両方 以内 以前 以後 任意 使用不可 使用可能 優先 優先順位 元
        元の 共有 共有された 共通 内 出典 初出 別 利用不可 利用可能 前 原典 原文 原本 双方 各 同じ 同一 変更なし 完全 後 後で 必要 必須 承認 承認済み 曖昧 最初
        未承認 未記入 条件 条件付き 欠落 正確 毎 異なる 登場 空の 空欄 空白 限り 除いて 除き 順 順序
        """.split()
    ),
}
