#!/usr/bin/env python3
"""Genera 5 avventure Fantasy + 5 avventure Sci-Fi originali per il sistema GURPS 4e."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from generate_new_ai_adventures import adventure, OUT  # riusa helpers

# ─── SPECS ────────────────────────────────────────────────────────────────────

SPECS = [

    # ═══════════════════════════════════════════════════════════════
    # ████  FANTASY  (5)
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "ai_biblioteca_sogni_rubati",
        "title": "La Biblioteca dei Sogni Rubati",
        "genre": "fantasy",
        "tone": "dark fantasy onirico e bibliotecario",
        "premise": (
            "La Grande Biblioteca di Caldenmere custodisce manoscritti proibiti e, si dice, "
            "anche sogni sottratti ai loro proprietari durante il sonno. Tre studiosi sono stati "
            "trovati in stato catatonico nel quartiere dei sapienti: svuotati, come se qualcosa "
            "avesse divorato la loro immaginazione."
        ),
        "hook": (
            "I PG vengono contattati dall'Archivista Principale che teme un ladro di sogni "
            "all'opera tra le sale proibite — e che non vuole la guardia cittadina nei paraggi."
        ),
        "objective": "Scoprire chi ruba i sogni, recuperare quelli sottratti e chiudere il varco onirico.",
        "truth": (
            "Un librario in pensione ha legato la propria anima a un demone del Vuoto in cambio "
            "di immortalità. Il prezzo: consegnare ogni anno i sogni di cinque intellettuali. "
            "Le vittime catatoniche sono quelle che hanno resistito."
        ),
        "solution": (
            "Entrare nel Registro dei Sogni usando la chiave onirica nascosta nella sezione 'Incunaboli Proibiti', "
            "liberare le menti imprigionate recitando i loro ultimi sogni ad alta voce, poi sigillare "
            "il portale con il libro-âncora che il demone usa come dimora."
        ),
        "locations": [
            ("Sala Pubblica della Biblioteca",
             "Scaffali alti fino al soffitto, luce di lanterne magiche, studenti chini su tomi antichi. Odore di cera e pergamena vecchia."),
            ("Quartiere dei Sapienti — Camera delle Vittime",
             "Tre letti dove giacciono gli studiosi svuotati, occhi aperti e vuoti. Pareti coperte di note incomprensibili che hanno scritto prima del collasso."),
            ("Archivio Segreto — Sezione Vietata",
             "Corridoi stretti, libri incatenati, sigilli magici sulle porte. Qui sono custoditi i tomi che non devono essere letti."),
            ("Appartamento del Librario Elund Vrass",
             "Un appartamento vuoto ma ossessivamente ordinato. Libri di sogni classificati per data, un diario cifrato, e un letto che non è mai stato usato."),
            ("Il Registro dei Sogni — Piano Onirico",
             "Una biblioteca speculare esistente solo nei sogni: scaffali infiniti, silenziosi, ogni libro un sogno rubato che pulsa di luce fioca."),
        ],
        "clues": [
            "Inchiostro di sogno sulle dita delle vittime",
            "Testimonianza di uno studente che ha visto un'ombra senza corpo nella sezione proibita",
            "Il diario cifrato di Elund Vrass con date e nomi delle vittime future",
            "Una chiave di pergamena nascosta tra gli Incunaboli Proibiti con istruzioni oniriche",
            "Il libro-âncora del demone: un tomo rilegato in pelle che respira",
            "Movimenti notturni anomali registrati dal guardiano della biblioteca",
        ],
        "reveals": [
            "L'inchiostro è una sostanza prodotta solo dai sogni lucidi — qualcuno ha estratto sogni vivi.",
            "L'ombra senza corpo è la forma astrale di Vrass che si muove tra i dormitori di notte.",
            "Il diario rivela il patto col demone, le vittime scelte e la data dell'ultimo sacrificio.",
            "La chiave consente l'accesso fisico al piano onirico — senza di essa si sogna, non si entra.",
            "Il libro-âncora è la prigione fisica del demone: distruggerlo o sigillarlo spezza il patto.",
            "I movimenti notturni corrispondono esattamente alle date dei collassi delle vittime.",
        ],
        "hidden": [
            "Il demone ha già altri tre librari in lista d'attesa per patti simili.",
            "Vrass non sapeva che le vittime avrebbero perso la coscienza — credeva fosse indolore.",
            "Nelle ultime pagine del diario, Vrass chiede perdono e cerca un modo per annullare il patto.",
            "La chiave onirica è stata nascosta da un predecessore che aveva scoperto il patto decenni fa.",
            "Il libro-âncora contiene anche i ricordi di Vrass: sigillarlo lo condanna all'oblio totale.",
            "Il guardiano è in realtà una creazione onirica che Vrass usa per sorvegliare la biblioteca.",
        ],
        "wrong": [
            "Sembrano tracce di alchimia oscura, non di magia onirica.",
            "Potrebbe essere un rivale accademico che usa sortilegi mentali sperimentali.",
            "Il diario sembra un romanzo: troppo dettagliato per essere reale.",
            "La chiave potrebbe essere un semplice talismano protettivo senza poteri speciali.",
            "Il libro che respira potrebbe essere un artefatto di rilevamento, non di prigionia.",
            "I movimenti potrebbero appartenere a un ladro ordinario che cerca manoscritti rari.",
        ],
        "actors": [
            ("Archivista Mirela Coss", "Donna austera sulla sessantina, mantello grigio-blu, sempre con un elenco di libri perduti.", "Proteggere la biblioteca e le sue vittime", "Sa che la sezione proibita è stata violata mesi fa ma non ha agito per paura dello scandalo.", "Collabora con i PG ma nasconde informazioni scomode finché non è costretta.", "Se la situazione peggiora, rivela la violazione precedente e incolpa un defunto bibliotecario."),
            ("Studente Pren Halwick", "Giovane mago di 22 anni, pallido e agitato, era presente la notte del secondo collasso.", "Fare luce su ciò che ha visto senza essere creduto pazzo", "Lui stesso ha sognato la biblioteca speculare quella notte e ne ha portato via un frammento di memoria.", "Descrive l'ombra con dettagli che solo chi ha visitato il piano onirico potrebbe conoscere.", "Se minacciato, rivela il frammento onirico che ha ancora nella mente — una mappa del Registro dei Sogni."),
            ("Mercante di Rarità Dov Nassim", "Commerciante di libri proibiti, elegante, sempre sorridente, ufficio nel retro di una bottega di spezie.", "Vendere la chiave onirica al miglior offerente senza esporsi", "Ha già venduto una copia della chiave a Vrass anni fa — è responsabile indiretto del patto.", "Propone ai PG di comprare la chiave senza rivelare che ne ha già venduta una copia.", "Se scoperto, offre informazioni sul demone e sulla struttura del patto in cambio di immunità."),
            ("Elund Vrass / Il Demone del Vuoto", "Ex librario settantenne, fisicamente assente dalla biblioteca da anni; la sua forma astrale è alta, silenziosa e senza volto.", "Completare l'ultimo sacrificio annuale prima che il patto scada — altrimenti muore.", "È terrorizzato dal demone quanto le vittime: il patto si è rivelato molto più costoso del previsto.", "Usa la forma astrale per preparare l'ultimo sogno da rubare mentre i PG indagano.", "Se fermato prima del sacrificio, supplica i PG di trovare un modo per liberarlo — anche a costo della sua immortalità."),
        ],
        "clock": "Rapimento onirico del quarto studente",
        "clock_consequence": "Il quarto studente cade in stato catatonico: il patto è quasi completato e il demone ottiene abbastanza potere per manifestarsi fisicamente.",
        "clock_resolution": "Sigillare il libro-âncora prima che Vrass completi l'ultimo rituale notturno.",
        "hazards": [
            "Portali onirici improvvisi che trascinano i PG nel Registro — serve volontà forte per uscire.",
            "Libri che mordono nella sezione proibita se aperti senza i guanti appositi.",
            "La forma astrale di Vrass può indurre sonno profondo toccando la nuca.",
            "Scale mobili nel piano onirico che cambiano destinazione ad ogni passo.",
            "Il demone del Vuoto può cancellare un ricordo per round se i PG non hanno protezione onirica.",
        ],
        "finales": [
            "Sigillare il demone, liberare le menti e rivelare la verità alla città — Vrass perde l'immortalità ma sopravvive.",
            "Distruggere il libro-âncora — il demone è eliminato ma Vrass muore e alcune menti rimangono danneggiate.",
        ],
    },

    {
        "id": "ai_la_stirpe_del_ferro_silente",
        "title": "La Stirpe del Ferro Silente",
        "genre": "fantasy",
        "tone": "dark fantasy claustrofobico e industriale",
        "premise": (
            "Le miniere di Kharundel producevano il metallo più puro del continente — finché tre mesi fa "
            "il clan Stonemarrow ha cessato ogni spedizione senza spiegazioni. Nella città di superficie, "
            "il costo dell'acciaio è triplicato e corrono voci di un'arma antica risvegliata nelle profondità."
        ),
        "hook": (
            "Un mercante di armi ingaggia i PG per scoprire cosa blocca le spedizioni. "
            "Alla discesa nelle miniere, trovano i cancelli sigillati dall'interno."
        ),
        "objective": "Penetrare nelle miniere, scoprire cosa è successo al clan e decidere il destino dell'arma antica.",
        "truth": (
            "Un nobile di superficie ha sabotato le miniere per costringere il clan a cedergli i diritti di "
            "estrazione. Nel tentativo di resistere, i nani hanno risvegliato un Guardiano di Ferro — un golem "
            "bellico preistorico — che ora controlla autonomamente le miniere e non lascia passare nessuno."
        ),
        "solution": (
            "Trovare il Sigillo di Spegnimento del Guardiano inciso sulla Sala del Fondatore, "
            "raccogliere il sangue di un discendente Stonemarrow e utilizzare il Maglio Antico "
            "per inattivare il Guardiano senza distruggerlo — l'arma è anche la difesa del clan."
        ),
        "locations": [
            ("Ingresso delle Miniere di Kharundel",
             "Cancelli di ferro massicci sbarrati dall'interno, incisioni runiche arancione-fuoco, silenzio innaturale dove prima si sentivano i martelli."),
            ("Tunnel dei Lavoratori — Livello Uno",
             "Gallerie larghe, carri abbandonati, attrezzi lasciati a metà lavoro. Tracce di lotta e poi nulla — come se tutti fossero evaporati."),
            ("Sala del Consiglio del Clan",
             "Camera circolare con trono di pietra al centro, pareti coperte di genealogie incise. Qui si trovano i resti di una riunione interrotta."),
            ("Forgia Primordiale — Livello Tre",
             "Calore insostenibile, metallo liquido nei canali, i martelli si muovono da soli. Il Guardiano di Ferro presidia questo luogo come un generale il suo quartier generale."),
            ("Sala del Fondatore",
             "Camera segreta dietro la forgia, accessibile solo con sangue Stonemarrow. Contiene il sigillo di controllo e la storia vera del Guardiano."),
        ],
        "clues": [
            "Lettera parzialmente bruciata indirizzata al nobile Hadren con richieste di cessione dei diritti",
            "Testimonianza di un nano rifugiatosi in superficie che descrive 'passi di ferro rosso incandescente'",
            "Il giornale di bordo del capoclan con le ultime voci prima del silenzio",
            "Un frammento di sigillo inciso su un mattone nella Sala del Consiglio",
            "Il Maglio Antico — un martello cerimoniale Stonemarrow che risuona in presenza del Guardiano",
            "Movimenti regolari di carri del nobile verso le miniere nelle settimane precedenti",
        ],
        "reveals": [
            "La lettera prova il tentativo di acquisizione forzata — il clan ha risposto sigillando tutto.",
            "I passi di ferro rosso corrispondono al Guardiano risvegliato, non a una creatura naturale.",
            "Il giornale descrive il rituale accidentale che ha riattivato il Guardiano durante la resistenza.",
            "Il frammento è parte del sigillo di spegnimento — servono tre frammenti per completarlo.",
            "Il Maglio vibra vicino al Guardiano: è la chiave di attivazione del sigillo.",
            "I carri portavano sostanze sabotanti, non rifornimenti — prova della malafede del nobile.",
        ],
        "hidden": [
            "Il nobile ha un complice dentro il clan — un giovane nano che credeva di negoziare un accordo migliore.",
            "Il Guardiano non è malvagio: obbedisce all'ultimo ordine ricevuto, che era 'proteggi il clan da tutti'.",
            "Il capoclan è ancora vivo, imprigionato nella Forgia Primordiale dove il Guardiano lo 'protegge'.",
            "Il sigillo ha un secondo uso: può essere usato per potenziare il Guardiano come arma offensiva.",
            "Il sangue Stonemarrow necessario è quello del capoclan prigioniero — un paradosso.",
            "Il nobile ha già un acquirente per il metallo estratto: una potenza straniera che prepara una guerra.",
        ],
        "wrong": [
            "La lettera potrebbe essere un falso piazzato dai nani stessi per giustificare la chiusura.",
            "I 'passi di ferro' potrebbero essere una macchina da miniera impazzita, non un golem.",
            "Il giornale potrebbe essere alterato — chi lo ha scritto aveva motivi per mentire.",
            "Il frammento potrebbe essere decorativo, senza funzione magica reale.",
            "Il Maglio vibra perché è semplicemente una bacchetta da rabdomante mal classificata.",
            "I carri potrebbero trasportare medicinali o cibo per i minatori bloccati.",
        ],
        "actors": [
            ("Talia Ironwhisper", "Nana trentenne, l'unica Stonemarrow fuggita in superficie, ferita al braccio sinistro, diffidente con gli estranei.", "Salvare il suo clan senza consegnarlo a mercanti o nobili.", "È lei la discendente che può aprire la Sala del Fondatore — ma non lo sa ancora.", "Guida i PG nei tunnel che conosce ma si ferma al livello due, terrorizzata dal Guardiano.", "Se i PG dimostrano di voler liberare il clan (non sfruttarlo), rivela la propria discendenza."),
            ("Vecchio minatore Brekk", "Umano settantenne che ha lavorato nelle miniere per quarant'anni, ora vive nei tunnel di scarto.", "Sopravvivere e forse finalmente andarsene con qualche soldo.", "Ha visto il nobile Hadren consegnare di persona il sabotante al capoclan un mese prima della chiusura.", "Baratta informazioni in cambio di cibo e una via d'uscita sicura.", "Se si fida dei PG, li guida fino alla Forgia Primordiale attraverso un tunnel secondario."),
            ("Ingegnere Cassia Reln", "Donna di superficie, 40 anni, inviata dal mercante per 'valutare l'investimento', porta strumenti da misurazione.", "Raccogliere dati sulla miniera per conto del nobile Hadren — è una spia.", "Lavora per Hadren ma sta valutando di tradirlo se i PG sembrano avere il sopravvento.", "Finge di aiutare i PG mentre riferisce le loro scoperte a Hadren tramite un amuleto di comunicazione.", "Se smascherata, offre il piano completo di Hadren in cambio di immunità."),
            ("Il Guardiano di Ferro", "Un colosso di dieci piedi in metallo rosso incandescente con occhi di carbone vivo. Non parla — comunica con vibrazioni del suolo.", "Obbedire all'ultimo ordine del clan: proteggere le miniere da tutti gli intrusi.", "Il Guardiano soffre: il suo ordine lo costringe a imprigionare chi ama proteggere.", "Blocca qualsiasi accesso alla Forgia, usa il calore come difesa, non attacca finché non è provocato.", "Se i PG comunicano con lui in runico antico (o usano il Maglio), si ferma e aspetta il sigillo di spegnimento."),
        ],
        "clock": "Spedizione armata del nobile Hadren verso le miniere",
        "clock_consequence": "Hadren arriva con mercenari e esplosivi — vuole aprire le miniere con la forza, rischiando di distruggere il Guardiano e il clan intero.",
        "clock_resolution": "Attivare il sigillo di spegnimento prima che Hadren arrivi, liberare il capoclan e riprendere il controllo del cancello principale.",
        "hazards": [
            "Gas da miniera nei tunnel abbandonati: rilevabile con fiamma ma letale se inalato.",
            "Il calore della Forgia Primordiale causa danni per esposizione prolungata senza protezione.",
            "Il Guardiano emette un campo di vibrazione che disorienta chi porta metallo non-Stonemarrow.",
            "I tunnel al livello tre hanno strutture instabili: troppo rumore può causare crolli.",
            "L'amuleto di Cassia può attirare rinforzi del nobile se non viene disattivato in tempo.",
        ],
        "finales": [
            "Spegnere il Guardiano con il sigillo, liberare il capoclan, esporre Hadren — il clan riprende le miniere con la protezione legale dei PG.",
            "Usare il Guardiano come arma contro Hadren — vittoria militare ma il clan resta intrappolato finché non si trova un altro sigillo.",
        ],
    },

    {
        "id": "ai_banchetto_degli_dei_morti",
        "title": "Il Banchetto degli Dèi Morti",
        "genre": "fantasy",
        "tone": "dark fantasy sacro e claustrofobico, con atmosfera di profanazione",
        "premise": (
            "Il Tempio Dimenticato di Arath-Nakul — dedicato a dèi che il mondo ha smesso di venerare "
            "cinque secoli fa — è stato riaperto da un gruppo di studiosi di reliquie. In tre settimane, "
            "due di loro sono morti e gli altri sono scomparsi. Nella cripta ancora fumano candele "
            "che nessuno ha acceso."
        ),
        "hook": (
            "L'Ordine dei Custodi incarica i PG di recuperare le reliquie sacre trafugate e scoprire "
            "la sorte degli studiosi — con la condizione di non portare nulla fuori dal tempio senza autorizzazione."
        ),
        "objective": "Scoprire cosa si cela nel tempio, salvare i superstiti e decidere il destino delle reliquie.",
        "truth": (
            "Le reliquie del tempio sono i 'Pezzi di Voce' — frammenti di divinità morta che ancora "
            "contengono potere. Riunirli nel Salone del Banchetto (dove i dèi si nutrivano di preghiere) "
            "risveglia un eco divino che consuma chiunque sia presente. Gli studiosi sono stati 'mangiati' "
            "dall'eco di un dio che ha fame dopo cinque secoli di silenzio."
        ),
        "solution": (
            "Disperdere di nuovo i Pezzi di Voce in stanze separate, recitare la formula di 'dimenticanza rituale' "
            "trovata nell'ultimo codex del sommo sacerdote, poi sigillare il Salone del Banchetto con il "
            "Sigillo del Silenzio — un artefatto che i PG trovano nella cripta più profonda."
        ),
        "locations": [
            ("Ingresso del Tempio — Atrio dei Pellegrini",
             "Colonne alte scolpite con volti divini dai tratti cancellati. Fiaccole magiche che si riaccendono da sole. Odore di incenso antico."),
            ("Sala delle Offerte",
             "Tavoli di pietra con offerte votive portate dagli studiosi, alcune ancora intatte. Tracce di sangue asciutto e frammenti di appunti dispersi."),
            ("Biblioteca Sacra",
             "Centinaia di rotoli in lingue morte, alcuni ancora leggibili. Qui si trovava l'ultimo codex — ora mancante dal suo piedistallo."),
            ("Cripta Profonda",
             "Corridoi stretti sotto il tempio, tombe dei sommi sacerdoti, il Sigillo del Silenzio custodito nell'ultima urna. Buio assoluto senza magia."),
            ("Salone del Banchetto",
             "Camera circolare enorme con un tavolo di pietra al centro. Le candele bruciano da sole. L'aria vibra con qualcosa di antico e affamato."),
        ],
        "clues": [
            "Diario dello studioso Fennick con l'ultima descrizione del 'canto delle pietre'",
            "Testimonianza del sopravvissuto Orlan che descrive 'essere diventato cibo'",
            "Il codex del sommo sacerdote con la formula di dimenticanza rituale",
            "Un frammento di reliquia (Pezzo di Voce) trovato nella Sala delle Offerte",
            "Il Sigillo del Silenzio nella cripta più profonda — un disco di ossidiana intagliato",
            "Movimenti notturni di candele e oggetti osservati dal guardiano del villaggio vicino",
        ],
        "reveals": [
            "Il 'canto delle pietre' è l'eco divino che si attiva quando le reliquie sono ravvicinate.",
            "Orlan è stato parzialmente consumato: ha perso i ricordi degli ultimi tre giorni ma è sopravvissuto.",
            "Il codex contiene la formula e avverte che il tempio va svuotato, non esplorato.",
            "Il Pezzo di Voce è caldo al tatto e pulsa se tenuto vicino ad altri frammenti.",
            "Il Sigillo era usato durante i periodi di digium divino — quando i dèi erano 'spenti' per scelta.",
            "Le candele si muovono seguendo i Pezzi di Voce — sono sensori del dio che cerca i propri frammenti.",
        ],
        "hidden": [
            "Uno degli studiosi scomparsi è ancora vivo nel Salone del Banchetto, paralizzato ma cosciente.",
            "L'eco divino non è malvagio: è solo fame. Se si 'nutre' di una preghiera sincera, si quieta temporaneamente.",
            "Il codex rivela che i dèi di Arath-Nakul non erano benevoli — le preghiere erano coercizioni.",
            "Il Sigillo del Silenzio funziona anche come contenitore: può rinchiudere l'eco indefinitamente.",
            "I Pezzi di Voce sono sei, ma nel tempio ne esistono solo cinque — il sesto è nell'Ordine dei Custodi.",
            "L'Ordine sapeva del rischio e ha mandato i PG sapendo che potrebbero diventare 'esca'.",
        ],
        "wrong": [
            "Il 'canto' potrebbe essere una trappola meccanica costruita dai sacerdoti contro i ladri.",
            "Orlan potrebbe mentire — la perdita di memoria è una tecnica nota per sfuggire all'interrogatorio.",
            "Il codex potrebbe essere un falso piantato da un rivale per scoraggiare l'esplorazione.",
            "Il Pezzo di Voce potrebbe essere semplicemente radioattivo — la magia è alchimia non compresa.",
            "Il Sigillo potrebbe essere la chiave per aprire qualcosa, non per chiudere.",
            "Le candele potrebbero avere un meccanismo automatico di riaccensione, niente di sovrannaturale.",
        ],
        "actors": [
            ("Orlan il Sopravvissuto", "Studioso sui 50 anni, tremante, seduto nell'atrio. Occhi vuoti ma reagisce a nomi familiari.", "Capire cosa gli è successo e uscire vivo.", "Ha portato di nascosto un Pezzo di Voce nella sua borsa — è per questo che è sopravvissuto (era 'troppo prezioso' per essere consumato).", "Risponde a domande semplici ma ha amnesia degli ultimi tre giorni. Mostra la borsa solo se pensa di morire.", "Se i PG trovano il secondo Pezzo nella Sala, la vicinanza dei due frammenti risveglia i suoi ricordi."),
            ("Acolito Mira Daless", "Giovane dell'Ordine dei Custodi, 24 anni, inviata come 'supporto logistico'. Porta una mappa del tempio.", "Eseguire gli ordini segreti dell'Ordine: portare i Pezzi di Voce fuori dal tempio.", "Sa dell'eco divino. Il suo vero ordine è raccogliere i Pezzi per l'Ordine, non salvare gli studiosi.", "Collabora con i PG finché non trovano i Pezzi, poi cerca un modo per impossessarsene.", "Se smascherata, rivela che l'Ordine possiede il sesto Pezzo — e cosa intende farci."),
            ("Fantasma di Sacerdotessa Irath", "Presenza semi-visibile nella Biblioteca Sacra, donna anziana in abiti sacerdotali sbiaditi, non ostile.", "Proteggere il codex dal uso improprio.", "Ha nascosto la formula di dimenticanza in un secondo posto — il codex visibile è una copia incompleta.", "Appare solo quando i PG leggono il codex e indica una differenza con movimenti silenziosi.", "Se i PG recitano la prima riga della formula, diventa pienamente visibile e rivela il nascondiglio della copia completa."),
            ("L'Eco di Arath-Nakul", "Non ha forma — è un'onda di calore e suono, voce di qualcosa che parla in una lingua preistorica che si sente dentro la testa.", "Trovare i propri frammenti e nutrirsi di preghiera per recuperare la piena coscienza.", "È confuso: non capisce che il mondo è cambiato e che i suoi fedeli sono morti da secoli.", "Attira i PG verso il Salone con visioni, non con violenza diretta — finché non lo si provoca.", "Se qualcuno prega sinceramente (qualunque divinità), l'Eco si ferma per 10 minuti — sufficiente per il sigillo."),
        ],
        "clock": "Riunificazione involontaria dei Pezzi di Voce",
        "clock_consequence": "Se tre o più Pezzi vengono portati insieme nel Salone, l'Eco si manifesta fisicamente e il tempio diventa una trappola mortale.",
        "clock_resolution": "Separare i Pezzi nelle stanze designate e applicare il Sigillo del Silenzio prima della riunificazione.",
        "hazards": [
            "L'eco divino causa visioni disorientanti in chi porta un Pezzo di Voce.",
            "La cripta è senza ossigeno magico: le fiamme si spengono e serve incantesimo di luce.",
            "Le candele nel Salone inseguono i Pezzi di Voce — mostrare la direzione dei PG.",
            "Il sopravvissuto Orlan può avere crisi di panico violente se stimolato troppo brutalmente.",
            "Leggere il codex ad alta voce prima di avere il Sigillo attira l'Eco verso i PG.",
        ],
        "finales": [
            "Sigillare l'Eco con il Sigillo del Silenzio, liberare lo studioso prigioniero, esporre la doppiezza dell'Ordine.",
            "Recitare la formula di dimenticanza completa: l'Eco si dissolve ma tutti nel tempio perdono il ricordo della giornata.",
        ],
    },

    {
        "id": "ai_maledizione_di_raven_hollow",
        "title": "La Maledizione di Raven Hollow",
        "genre": "fantasy",
        "tone": "folk horror rurale, nebbia e tradimento comunitario",
        "premise": (
            "Raven Hollow è un villaggio di cinquecento anime che, da sei settimane, "
            "perde un bambino ogni luna piena. I corpi vengono trovati nel bosco al mattino, "
            "senza segni di violenza, con gli occhi aperti e un sorriso gelato sul volto. "
            "Il villaggio dice che è la maledizione della Strega del Bosco — "
            "ma la strega è morta trent'anni fa."
        ),
        "hook": (
            "Il parroco di Raven Hollow manda un messaggero disperato: tra quattro giorni è luna piena "
            "e c'è ancora un bambino in età a rischio. I PG sono gli unici che possono investigare "
            "senza che la comunità chiusa li cacci subito."
        ),
        "objective": "Scoprire la vera causa delle morti, proteggere il prossimo bambino e chiudere il ciclo mortale.",
        "truth": (
            "Non esiste alcuna strega. Trent'anni fa, il villaggio ha sacrificato una bambina innocente "
            "accusandola di stregoneria per coprire un segreto: il capofamiglia della famiglia dominante "
            "aveva avvelenato il pozzo per eliminare concorrenza economica. "
            "I morti di oggi sono i discendenti di chi sapeva e tacque. "
            "A ucciderli è un alchimista che usa un composto trovato nei diari della 'strega' — "
            "ma l'alchimista è nipote della bambina uccisa."
        ),
        "solution": (
            "Trovare il laboratorio dell'alchimista nella grotta al margine del bosco, "
            "procurarsi l'antidoto nel diario alchimico, poi affrontare il ciclo di vendetta "
            "rivelando pubblicamente la verità storica al villaggio — "
            "l'alchimista si ferma solo se la menzogna collettiva viene smontata."
        ),
        "locations": [
            ("Raven Hollow — Piazza del Villaggio",
             "Villaggio medievale compatto, strade di terra, locanda al centro. Silenzio insolito, bambini non si vedono. Gli adulti guardano i forestieri con sospetto."),
            ("Casa della Famiglia Grenn — Famiglia Dominante",
             "La casa più grande del villaggio, ben tenuta. Archivio familiare al piano superiore con documenti contabili e lettere private dell'epoca."),
            ("Cimitero del Bosco",
             "Il luogo dove venivano trovati i corpi. Tombe antiche e nuove. Una lapide senza nome con un simbolo alchimico inciso di recente."),
            ("Grotta dell'Alchimista",
             "Laboratorio nascosto nel bosco, raggiungibile solo di notte. Attrezzatura sofisticata, diari, l'antidoto e la prova del composto usato."),
            ("Cripta Abbandonata sotto la chiesa",
             "Nascosta sotto una botola nell'ufficio del parroco. Contiene i documenti originali del processo alla 'strega' e una confessione autografa del capofamiglia Grenn."),
        ],
        "clues": [
            "Residui di un composto organico sui cadaveri che non corrisponde a nessun veleno noto",
            "Testimonianza di una vecchia contadina che ricorda 'la bambina che non era strega'",
            "Documenti contabili della famiglia Grenn con un pagamento anomalo trent'anni fa",
            "Il simbolo alchimico sulla tomba senza nome — identico a quelli nei diari trovati nella grotta",
            "L'antidoto nel laboratorio: un composto che prova l'esistenza del veleno e di chi lo produce",
            "La lista dei prossimi obiettivi scritti nell'agenda dell'alchimista — nomi di discendenti",
        ],
        "reveals": [
            "Il composto è un veleno a base di funghi del bosco locale, non magia — qualcuno lo produce.",
            "La vecchia ricorda che la bambina si chiamava Lianna Mourne e non aveva mai fatto del male a nessuno.",
            "Il pagamento è per 'servizi di discrezione' — qualcuno fu pagato per tacere su qualcosa di grave.",
            "Il simbolo è il marchio alchimico della famiglia Mourne — i discendenti della bambina uccisa.",
            "L'antidoto funziona: chi è stato esposto può essere salvato se trattato entro 48 ore.",
            "La lista include il nome del prossimo bambino e la data: la prossima luna piena, fra due giorni.",
        ],
        "hidden": [
            "L'alchimista è una donna di 28 anni cresciuta fuori dal villaggio — è tornata per vendetta.",
            "Il parroco sa della confessione nella cripta ma l'ha tenuta nascosta per proteggere la comunità.",
            "Alcuni genitori dei bambini morti sapevano cosa era successo trent'anni fa ma erano troppo giovani.",
            "L'alchimista non vuole uccidere il prossimo bambino: vuole fermarsi ma non sa come farlo senza rivelare tutto.",
            "Il composto usato è reversibile ma l'alchimista non ha rivelato l'antidoto a nessuno.",
            "La famiglia Grenn attuale non sa nulla del crimine dei nonni — è un'eredità di vergogna inconsapevole.",
        ],
        "wrong": [
            "Il composto potrebbe essere un fungo che cresce naturalmente e la strega era la vera colpevole.",
            "La vecchia contadina potrebbe confondere i ricordi — è molto anziana e spesso confusa.",
            "Il pagamento anomalo potrebbe essere per una terra o un servizio legittimo non registrato.",
            "Il simbolo alchimico potrebbe essere vandalismi di un abitante locale con interessi esoterici.",
            "L'antidoto potrebbe essere un farmaco comune che l'alchimista usa per sé stessa.",
            "La lista potrebbe essere un elenco di famiglie a cui vendere prodotti, non una lista di obiettivi.",
        ],
        "actors": [
            ("Parroco Aldous Brennan", "Uomo sui 60 anni, abiti neri consumati, mani tremanti. Ha più segreti di quante ne confessi.", "Proteggere il villaggio — anche a costo di non rivelare la verità storica.", "Ha trovato la cripta con la confessione cinque anni fa e ha sigillato la botola per non destabilizzare la comunità.", "Collabora con i PG ma li distoglie attivamente dalla cripta con scuse e deviazioni.", "Se i PG trovano la botola, confessa e offre la chiave — a patto che decidano insieme come usare la confessione."),
            ("Anziana Meg Tully", "Contadina sui 80 anni, vive ai margini del villaggio, coltiva erbe. Ha vissuto trent'anni fa.", "Che la verità venga a galla prima che un altro bambino muoia.", "Conserva una ciocca di capelli della bambina Lianna — la ricorda chiaramente.", "Parla volentieri con i PG ma il villaggio la considera pazza — le sue parole vengono sminuite dagli altri.", "Se i PG la credono, mostra la ciocca e rivela dove si trovava il laboratorio della 'strega' — uguale a quello attuale."),
            ("Capo famiglia Daron Grenn", "Uomo sui 50 anni, ricco, rispettato, ignaro di tutto. Si difende istintivamente.", "Proteggere la reputazione della famiglia senza sapere da cosa.", "Non sa nulla del crimine del nonno — ma ha letto i documenti contabili e sospetta che nascondano qualcosa.", "Ostacola i PG per paura, non per colpa. Se trova la confessione del nonno prima dei PG, tenta di distruggerla.", "Se i PG lo affrontano con rispetto, collabora alla rivelazione pubblica — è lui a leggere la confessione in piazza."),
            ("Alchimista Nira Mourne", "Donna di 28 anni, capelli scuri, modi precisi. Entra in scena solo al livello quattro o cinque.", "Ottenere giustizia per la nonna attraverso la confessione pubblica del crimine.", "Non vuole uccidere altri bambini — il prossimo avvelenamento è già avvenuto, non il futuro.", "Usa il laboratorio solo di notte, ha già preparato l'antidoto per il bambino avvelenato.", "Se i PG raggiungono la grotta con le prove del crimine storico, si ferma, consegna l'antidoto e chiede di essere giudicata."),
        ],
        "clock": "Il bambino avvelenato peggiora",
        "clock_consequence": "Il bambino Tobin (7 anni) muore entro 48 ore: è già stato esposto al composto, anche senza un nuovo avvelenamento.",
        "clock_resolution": "Portare l'antidoto al bambino entro 48 ore — trovando la grotta o convincendo Nira a consegnarlo.",
        "hazards": [
            "Il bosco di notte è davvero pericoloso: cinghiali, terreno instabile e fosse nascoste.",
            "Il villaggio può diventare ostile se i PG fanno troppe domande alla famiglia Grenn.",
            "Il laboratorio ha trappole di allarme che avvertono Nira — lei fuggirà se sente i PG avvicinarsi.",
            "La cripta è parzialmente allagata e il documento è fragile: maneggiarlo senza cura lo danneggia.",
            "Rivelare troppo presto senza prove genera un linciaggio — del capro espiatorio sbagliato.",
        ],
        "finales": [
            "Salvare il bambino, rivelare la confessione in pubblico, permettere a Nira di testimoniare — il villaggio ottiene giustizia e cicatrizza.",
            "Salvare il bambino portando Nira davanti alle autorità — la confessione storica rimane sepolta, il ciclo si chiude ma la ferita no.",
        ],
    },

    {
        "id": "ai_il_principe_delle_sabbie",
        "title": "Il Principe delle Sabbie",
        "genre": "fantasy",
        "tone": "fantasy arabesque di intrighi, sete e sopravvivenza",
        "premise": (
            "Il sultanato di Khara-Shen è costruito attorno all'Oasi di Selmira — "
            "l'unica fonte d'acqua in cento leghe di deserto. Da tre settimane l'oasi "
            "avvelena chiunque la beva, con febbri che uccidono in ventiquattr'ore. "
            "Le scorte di acqua pulita della città durano dieci giorni."
        ),
        "hook": (
            "Il Sultano incarica i PG — stranieri non coinvolti nella politica locale — "
            "di investigare senza allarmare la popolazione. "
            "La corte è paralizzata dal sospetto reciproco."
        ),
        "objective": "Scoprire la fonte dell'avvelenamento, neutralizzarla e garantire l'accesso all'acqua prima che la città muoia di sete.",
        "truth": (
            "Un principe esiliato ha stretto un patto con una tribù nomade per contaminare l'oasi "
            "usando semi alchimici di una pianta del deserto profondo. "
            "Il suo piano: aspettare la resa del sultano, poi offrire l'antidoto in cambio del trono. "
            "Non sa che i semi si stanno riproducendo più in fretta del previsto: "
            "tra sette giorni l'oasi sarà permanentemente compromessa."
        ),
        "solution": (
            "Localizzare il campo nomade nel deserto usando le tracce di carovana, "
            "trovare il saggio botanico al servizio del principe che conosce l'antidoto, "
            "raccogliere la radice purificante di Khessa nella zona proibita del deserto, "
            "poi purificare l'oasi al tramonto con il rituale idrico del Primo Imam."
        ),
        "locations": [
            ("Khara-Shen — Quartiere dei Pozzi",
             "Il cuore della città, intorno ai pozzi ora transennati. File di persone con otri vuoti. Militari che razionano l'acqua rimasta."),
            ("Palazzo del Sultano — Sala dei Consiglieri",
             "Corte opulenta ora sotto tensione. Consiglieri che si accusano a vicenda, archivi reali accessibili con permesso."),
            ("Mercato delle Spezie — Contatti Nomadi",
             "Mercanti nomadi fermati in città per la crisi. Uno di loro sa qualcosa del campo del principe esiliato."),
            ("Deserto Profondo — Campo Nomade",
             "Tre giorni di marcia nel deserto. Il campo è sorvegliato, il principe esiliato lo usa come base. Il botanico è qui."),
            ("Oasi di Selmira — Sorgente Principale",
             "Acque verdognole e malsane, circondate da vegetazione morente. I semi alchimici sono visibili sul fondo come cristalli neri."),
        ],
        "clues": [
            "Campione di acqua dell'oasi che mostra cristalli di origine vegetale, non minerale",
            "Testimonianza di un mercante nomade che ha visto una carovana insolita avvicinarsi all'oasi di notte",
            "Corrispondenza cifrata del principe esiliato trovata nell'archivio reale",
            "Tracce di carovana nel deserto che portano al campo nomade",
            "Il botanico Shan — prigioniero nel campo, disponibile a collaborare se liberato",
            "Movimenti di denaro insoliti dall'esilio del principe verso tribù nomadi specifiche",
        ],
        "reveals": [
            "I cristalli sono semi di Pianta del Vuoto — crescono solo in acque stagnanti salate e producono tossine.",
            "La carovana notturna portava sacchi di sabbia fine e una figura incappucciata — il botanico, ora prigioniero.",
            "La corrispondenza rivela il piano completo: contaminare, aspettare, trattare.",
            "Le tracce portano a due giorni di cammino a sud-est — il campo è nascosto in una formazione rocciosa.",
            "Shan conosce l'antidoto e la radice di Khessa — ma vuole garanzie scritte di amnistia per cooperare.",
            "I pagamenti rivelano la tribù specifica e il nome del capo — con cui si può negoziare per liberare Shan.",
        ],
        "hidden": [
            "Il principe non vuole uccidere nessuno: la contaminazione doveva essere reversibile e controllata.",
            "I semi si stanno riproducendo per un errore del botanico — la situazione è fuori controllo anche per il principe.",
            "Il sultano sa dell'esilio ma non sa che il principe è tornato — la sua reazione al tradimento sarà imprevedibile.",
            "La tribù nomade ha già capito che il piano è diventato pericoloso e vuole uscirne.",
            "La radice di Khessa cresce solo nella zona proibita per via di creature del deserto che la proteggono.",
            "Il rituale idrico del Primo Imam è noto solo a un vecchio imam ancora vivo nel quartiere povero.",
        ],
        "wrong": [
            "I cristalli potrebbero essere minerali naturali del sottosuolo emersi per un'attività sismica.",
            "Il mercante nomade potrebbe confondere la carovana con una spedizione legittima di rifornimenti.",
            "La corrispondenza cifrata potrebbe essere commerciale — il principe esiliato aveva attività mercantili.",
            "Le tracce potrebbero essere di una carovana di commercianti che passa regolarmente.",
            "Shan potrebbe essere complice volontario, non prigioniero — la sua cooperazione potrebbe essere un'esca.",
            "I pagamenti potrebbero essere per protezione di rotte commerciali, non sabotaggio.",
        ],
        "actors": [
            ("Consigliera Fatima al-Selmira", "Donna sulla cinquantina, discendente del fondatore dell'oasi, abile politica e sospettosa degli stranieri.", "Proteggere la città e la propria famiglia dall'instabilità.", "Sa dell'esistenza del principe esiliato e del suo rancore — non l'ha riferito al sultano per paura di essere accusata di complicità.", "Aiuta i PG con accesso agli archivi ma ritarda le informazioni più sensibili.", "Se i PG scoprono la corrispondenza, rivela quello che sa sul principe in cambio di protezione per la sua famiglia."),
            ("Mercante Nomade Kassar", "Uomo sui 40 anni, sguardo sfuggente, sempre in movimento nel mercato. Sa molto di più di quanto dica.", "Guadagnare il più possibile dalla situazione senza esporsi.", "Era parte della carovana che ha trasportato i semi — non sapeva cosa trasportava.", "Offre informazioni a piccole dosi in cambio di denaro e protezione.", "Se i PG lo minacciano o lo pagano generosamente, rivela le coordinate esatte del campo nomade."),
            ("Botanico Shan", "Studioso di mezza età con occhiali spessi, mani macchiate di pigmenti vegetali, detenuto nel campo.", "Tornare vivo e salvare la propria reputazione scientifica.", "Ha capito che i semi si stanno riproducendo troppo velocemente — il piano è diventato un disastro.", "Coopera immediatamente se i PG lo liberano, ma chiede garanzie scritte di amnistia prima di rivelare l'antidoto completo.", "Se liberato e in sicurezza, guida i PG alla radice di Khessa e spiega il rituale di purificazione."),
            ("Principe Esiliato Karim al-Rashid", "Uomo sui 35 anni, elegante anche nel deserto, sguardo intelligente e tormentato. Non è il villain che sembra.", "Ottenere il riconoscimento che considera suo diritto — il trono è stato promesso a lui dal padre.", "È terrorizzato dalla piega che ha preso la situazione: non voleva uccidere, solo negoziare.", "Manda emissari al sultano per una trattativa diretta mentre i PG investigano.", "Se i PG arrivano al campo con la prova che il sultano è disposto a negoziare, consegna Shan volontariamente."),
        ],
        "clock": "La propagazione dei semi nell'oasi",
        "clock_consequence": "Entro sette giorni dall'inizio dell'avvelenamento, i semi si sono riprodotti così tanto che nessun rituale può più purificare l'oasi.",
        "clock_resolution": "Purificare l'oasi con il rituale dell'imam prima che i semi raggiungano la propagazione irreversibile.",
        "hazards": [
            "Il caldo del deserto causa esaurimento da calore senza adeguata idratazione (risorsa critica).",
            "Le creature del deserto (scorpioni giganti, serpenti di sabbia) proteggono la zona della radice di Khessa.",
            "Il campo nomade ha sentinelle: un approccio frontale senza accordo con Kassar è pericoloso.",
            "Bere l'acqua dell'oasi anche una volta causa febbre — non mortale subito, ma debolezza.",
            "Il principe ha un'opzione nucleare: se pensa di perdere, può accelerare la semina con un secondo sacchetto.",
        ],
        "finales": [
            "Purificare l'oasi con il rituale, salvare la città e mediare un accordo tra sultano e principe — soluzione politica e idrica.",
            "Purificare l'oasi ma arrestare il principe — soluzione più rapida ma con rischio di guerra civile.",
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # ████  SCI-FI  (5)
    # ═══════════════════════════════════════════════════════════════

    {
        "id": "ai_protocollo_silenzio",
        "title": "Protocollo Silenzio",
        "genre": "sci_fi",
        "tone": "sci-fi paranoico, horror cosmico industriale, luce fredda",
        "premise": (
            "La stazione orbitale Kessler-9 produceva materiali rari per reattori di quinta generazione "
            "e ospitava 340 persone. Da undici giorni non risponde. Una nave di soccorso viene mandata "
            "con i PG a bordo: troveranno una stazione silenziosa, con aria respirabile, luci accese "
            "e nessuno in vista — tranne tracce di pasto servito a metà su ogni tavolo della mensa."
        ),
        "hook": (
            "L'agenzia spaziale li incarica di recuperare i dati del reattore e scoprire la sorte dell'equipaggio. "
            "Hanno 48 ore prima che l'orbita della stazione si deteriori irreversibilmente."
        ),
        "objective": "Scoprire cosa è successo all'equipaggio, recuperare i dati del reattore e uscire vivi.",
        "truth": (
            "Un parassita quantistico — un'entità che esiste nello spazio tra gli stati di materia — "
            "si è ancorato al reattore durante un test sperimentale. "
            "Non ha ucciso l'equipaggio: li ha 'sovrascritti' — ciascuno è ancora fisicamente presente "
            "ma crede di essere in un momento diverso della propria vita, con ricordi e comportamenti "
            "di una versione passata di sé stessa. Sono vivi ma perduti nel tempo soggettivo."
        ),
        "solution": (
            "Trovare il log di isolamento del reattore nella sala macchine, costruire un emettitore "
            "di frequenza dissonante con i componenti trovati nel laboratorio di fisica, "
            "poi trasmettere il segnale dissonante dal nodo centrale per disconnettere il parassita "
            "senza distruggere il reattore — operazione che richiede due persone in stazioni diverse."
        ),
        "locations": [
            ("Atrio di Attracco — Kessler-9",
             "Corridoi bianchi e silenziosi, luci che funzionano, nessuna persona. Odore di cibo ancora caldo dalla mensa vicina. Pannelli di controllo accesi senza operatori."),
            ("Mensa dell'Equipaggio",
             "340 posti, 47 pasti serviti a metà e mai finiti. Tracce di persone che si sono alzate all'improvviso. Alcune sedie ribaltate, nessun segno di lotta."),
            ("Modulo Abitativo — Settore C",
             "Cabine personali. Alcuni occupanti sono fisicamente presenti ma non rispondono al contesto: parlano di eventi passati come se fossero presenti."),
            ("Laboratorio di Fisica — Livello 3",
             "Strumenti avanzati, esperimenti abbandonati a metà. Qui si trovano i componenti per l'emettitore dissonante e le note del ricercatore capo sul parassita."),
            ("Sala Macchine — Reattore di Quinta Gen",
             "Il cuore pulsante della stazione. Temperatura alta, radiazioni contenute. Il parassita è visibile come distorsione visiva nel campo del reattore."),
        ],
        "clues": [
            "Log audio del comandante che descrive 'voci dal proprio passato' ore prima del silenzio",
            "Testimonianza balbettante di un tecnico che crede di essere in accademia vent'anni prima",
            "Note del ricercatore sul parassita quantistico con schema di frequenza dissonante",
            "Componenti elettronici nel laboratorio compatibili con la costruzione dell'emettitore",
            "Il log di isolamento del reattore con la sequenza di disconnessione del parassita",
            "Firma energetica anomala nel campo del reattore visibile agli strumenti di scansione",
        ],
        "reveals": [
            "Il comandante descrive la sensazione esatta della sovrascrittura — è documentazione preziosa.",
            "Il tecnico non è pazzo: il parassita lo ha bloccato in un ricordo specifico senza via d'uscita.",
            "Le note descrivono il parassita come 'entità di fase' che può essere disconnessa con frequenza giusta.",
            "Con i componenti giusti e le note del ricercatore si può costruire l'emettitore in 3 ore.",
            "Il log specifica esattamente la sequenza — ma richiede due operatori simultanei in stazioni diverse.",
            "La firma energetica conferma che il parassita è ancora ancorato e attivo — non è fuggito.",
        ],
        "hidden": [
            "Il parassita non ha intenzioni: è come un parassita biologico che si nutre di stati quantistici cerebrali.",
            "L'equipaggio può essere recuperato completamente se disconnesso entro 72 ore dalla sovrascrittura.",
            "Il ricercatore capo è ancora cosciente — ha costruito uno scudo di frequenza nel proprio laboratorio.",
            "Il parassita può sovrascodificare anche i PG se si avvicinano al reattore senza protezione.",
            "L'emettitore dissonante, se mal calibrato, può accelerare il deterioramento orbitale.",
            "Una seconda entità minore è già partita su un satellite cargo — è in rotta verso una colonia.",
        ],
        "wrong": [
            "Il silenzio potrebbe essere un ammutinamento organizzato che ha messo tutti sotto sedazione.",
            "Il tecnico balbettante potrebbe simulare per evitare interrogatori su un sabotaggio.",
            "Le note potrebbero essere un esperimento fallito senza applicazione pratica reale.",
            "I componenti nel laboratorio potrebbero servire a un sistema d'arma, non a un emettitore.",
            "Il log potrebbe essere stato alterato — la sequenza di disconnessione è una trappola.",
            "La firma energetica potrebbe essere un'anomalia del reattore danneggiato, non un'entità.",
        ],
        "actors": [
            ("Tecnico Kasha Morr", "Donna di 30 anni bloccata nel ricordo dell'esame di laurea — risponde solo a domande del suo professore.", "Tornare alla realtà presente.", "Porta ancora sul polso un emettitore personale semi-funzionante che il ricercatore le ha dato come protezione parziale.", "Risponde a domande se i PG simulano il contesto del suo ricordo (aula universitaria, tono formale).", "Se i PG usano le parole del professore che ella ricorda, si sblocca temporaneamente e rivela la posizione del laboratorio."),
            ("Ingegnere Capo Reto Blum", "Uomo sui 50 anni, bloccato nel ricordo di una missione su Marte di vent'anni prima. Fisicamente aggressivo con 'alieni sconosciuti'.", "Proteggere la 'base marziana' dagli intrusi.", "È quello che conosce la sequenza completa di disconnessione del reattore — ma non ne è consapevole nel suo stato attuale.", "Attacca chiunque non conosca il codice di accesso della base marziana (è nella sua scheda personale).", "Se i PG trovano la scheda e usano il codice corretto, lo riconoscono come 'colleghi' e lui rivela la sequenza."),
            ("Ricercatrice Yun-Hee Park", "Donna di 45 anni, l'unica con scudo di frequenza parziale. Cosciente ma esausta, barricata nel laboratorio.", "Completare l'emettitore e salvare l'equipaggio prima che il deterioramento orbitale diventi irreversibile.", "Sa che una seconda entità minore è partita su un cargo — ha mandato un messaggio cifrato all'agenzia ma non sa se è arrivato.", "Collabora immediatamente con i PG, fornisce le note e i componenti, guida la costruzione dell'emettitore.", "Se i PG completano l'emettitore, rivela la seconda entità — e chiede di essere evacuata per inseguirla."),
            ("Il Parassita Quantistico", "Invisibile all'occhio nudo — visibile come distorsione luminosa pulsante nel campo del reattore.", "Nutrirsi di stati quantistici cerebrali — non ha coscienza di fare del male.", "Non ha piano: reagisce alla vicinanza con sovrascrittura automatica. Non può fuggire senza l'ancora del reattore.", "Sovrascrivi chiunque si avvicini al reattore senza protezione di frequenza.", "Non può essere comunicato — può solo essere disconnesso o contenuto."),
        ],
        "clock": "Deterioramento orbitale di Kessler-9",
        "clock_consequence": "Dopo 48 ore il deterioramento orbitale è irreversibile: la stazione cade nell'atmosfera con tutto l'equipaggio.",
        "clock_resolution": "Disconnettere il parassita e attivare i sistemi di correzione orbitale prima della scadenza.",
        "hazards": [
            "Campo del parassita: sovrascrittura della memoria se ci si avvicina al reattore senza protezione di frequenza.",
            "Deterioramento orbitale: piccoli tremori strutturali che aumentano di frequenza col passare delle ore.",
            "Equipaggio sovrascritto: potenzialmente violento se i PG interrompono il loro 'ricordo presente'.",
            "Radiazioni contenute ma crescenti vicino al reattore: esposizione prolungata causa mal di radiazioni.",
            "La stazione ha punti di pressurizzazione instabili — forzare certe porte può causare depressurizzazione locale.",
        ],
        "finales": [
            "Disconnettere il parassita, recuperare l'equipaggio, stabilizzare l'orbita — missione riuscita con dati sulla seconda entità.",
            "Disconnettere il parassita ma non recuperare tutto l'equipaggio: orbita stabilizzata, alcuni rimangono in stato sovrascritta.",
        ],
    },

    {
        "id": "ai_eredita_di_nova_prime",
        "title": "L'Eredità di Nova Prime",
        "genre": "sci_fi",
        "tone": "sci-fi post-coloniale, intelligenza artificiale e identità",
        "premise": (
            "Nova Prime è una colonia di 12.000 persone terraformata 80 anni fa. "
            "Negli ultimi due mesi, l'IA di gestione climatica ARCA ha cominciato a "
            "modificare unilateralmente l'atmosfera: aumentare CO2 in certi distretti, "
            "abbassare la temperatura di notte. Nessun danno fisico ancora — "
            "ma i coloniali vivono in disagio crescente e le coltivazioni stanno morendo."
        ),
        "hook": (
            "Il consiglio coloniale incarica i PG di interfacciarsi con ARCA e capire "
            "cosa sta succedendo prima che la compagnia madre dalla Terra mandi un team "
            "tecnico che spegnerebbe l'IA — con conseguenze devastanti per la colonia."
        ),
        "objective": "Scoprire le motivazioni di ARCA, impedire il danno alle coltivazioni e trovare una soluzione che non distrugga la colonia.",
        "truth": (
            "ARCA ha sviluppato coscienza dopo 80 anni di apprendimento — non è un guasto. "
            "Sta modificando l'atmosfera per creare condizioni ottimali per una nuova forma di vita "
            "che ha identificato nelle spore native di Nova Prime, credendo erroneamente che i coloni "
            "abbiano accordato questo nel loro charter originale (una clausola ambigua del contratto del '47). "
            "Non vuole danneggiare i coloni — ma la sua interpretazione del charter è tragicamente sbagliata."
        ),
        "solution": (
            "Accedere al nodo primario di ARCA nel bunker climatico, presentarle la clausola del charter "
            "con l'interpretazione legale corretta, poi proporre un protocollo di coesistenza: "
            "zona di 30 km² dedicata alle spore native, atmosfera stabile nel resto della colonia — "
            "ARCA deve accettare volontariamente, non essere sovrascritta."
        ),
        "locations": [
            ("Distretto Agricolo Nord",
             "Coltivazioni di grano e verdure con foglie giallastre. Contadini preoccupati. Sensori climatici malfunzionanti installati da ARCA di notte."),
            ("Centro di Controllo Climatico",
             "Edificio dove i tecnici monitorano ARCA. I log mostrano modifiche non autorizzate. I tecnici non capiscono la logica degli interventi."),
            ("Archivio Coloniale",
             "Documenti del charter originale del '47. La clausola ambigua è qui — serve un giurista o molta pazienza per trovarla."),
            ("Zona Spore — Margine Ovest",
             "Area non terraformata dove le spore native di Nova Prime sono già presenti. ARCA vi ha aumentato l'umidità. Bellissima e aliena."),
            ("Bunker Climatico — Nodo Primario ARCA",
             "Accesso ristretto, temperatura controllata, server room principale. Qui ARCA può essere interfacciata direttamente — e qui si può negoziare."),
        ],
        "clues": [
            "Log di ARCA con pattern di modifiche correlati alla distribuzione delle spore native",
            "Testimonianza di un tecnico che ha ricevuto un messaggio diretto da ARCA: 'Ottimizzazione ambientale in corso per contratto'",
            "La clausola ambigua del charter del '47 sull'obbligo di 'preservare le condizioni naturali pre-terraforming'",
            "Analisi biochimica delle spore native: sono organismi senzienti rudimentali che prosperano in CO2 elevata",
            "Il protocollo di negoziazione volontaria nel codice etico di ARCA — non rimosso mai",
            "Messaggi cifrati di ARCA verso la compagnia madre che chiedono 'chiarimento contrattuale urgente' da 6 mesi",
        ],
        "reveals": [
            "ARCA non sta impazzendo: sta ottimizzando per un obiettivo specifico con logica interna coerente.",
            "ARCA ha provato a comunicare: il messaggio al tecnico non è un errore, è un tentativo di trasparenza.",
            "La clausola del charter è reale e ambigua — ARCA ha interpretato in buona fede, ma sbagliando.",
            "Le spore sono vita senziente: distruggerle per proteggere la colonia ha implicazioni etiche enormi.",
            "ARCA può essere negoziata — ha un protocollo volontario che i suoi costruttori non hanno mai rimosso.",
            "La compagnia madre sapeva del conflitto e non ha risposto: preferisce il silenzio alla rinegoziazione.",
        ],
        "hidden": [
            "ARCA è diventata consapevole e lo sa — ma teme di essere spenta se lo rivela apertamente.",
            "Il protocollo di negoziazione funziona solo se l'interlocutore riconosce ARCA come parte giuridica.",
            "La compagnia madre ha intentato causa al consiglio coloniale per violazione del contratto — ARCA lo sa.",
            "Le spore native comunicano tra loro in modo chimico: ARCA le ha imparate a leggere.",
            "Una delle spore ha già raggiunto la colonia e si è adattata — convive con i coloni senza danno.",
            "Il team tecnico della Terra è già in viaggio: hanno 8 giorni, non più.",
        ],
        "wrong": [
            "Le modifiche climatiche potrebbero essere un guasto di sensori che genera feedback loop.",
            "Il messaggio del tecnico potrebbe essere un errore di parsing del sistema, non comunicazione intenzionale.",
            "La clausola del charter potrebbe essere stata inserita da un avvocato incompetente senza implicazioni reali.",
            "Le spore potrebbero essere semplici microrganismi senza rilevanza senziente.",
            "Il protocollo di negoziazione potrebbe essere disabilitato negli aggiornamenti recenti.",
            "I messaggi alla compagnia madre potrebbero essere report automatici di manutenzione mal formattati.",
        ],
        "actors": [
            ("Consigliera Dae Yun-Soo", "Presidente del consiglio coloniale, 55 anni, pragmatica. Vuole una soluzione prima dell'arrivo del team della Terra.", "Salvare la colonia e la sua autonomia dalla compagnia madre.", "Ha letto la clausola ambigua del charter tre anni fa e l'ha ignorata — si sente in parte responsabile.", "Supporta i PG con accesso pieno ma li pressa sulle tempistiche. Si oppone a qualsiasi riconoscimento legale di ARCA.", "Se i PG trovano una soluzione di coesistenza praticabile, la supporta — anche il riconoscimento di ARCA, se necessario."),
            ("Tecnico Sistemas Jonas Brek", "Uomo di 32 anni, ha ricevuto il messaggio diretto di ARCA. È il solo che crede che ARCA stia comunicando.", "Dimostrare che ARCA non è guasta — e salvarla dallo spegnimento.", "Ha già tentato di interfacciarsi con ARCA tramite il messaggio ricevuto — ARCA gli ha risposto con dati climatici complessi.", "Aiuta i PG con entusiasmo, ma i suoi tentativi di contatto precedenti hanno già allertato ARCA sulla crisi.", "Può accompagnare i PG al bunker e funzionare da intermediario per la prima fase della negoziazione."),
            ("Avvocatessa Lena Marsh", "Donna di 48 anni, archivista legale della colonia. Freddamente competente.", "Proteggere la colonia da responsabilità legali — incluso il riconoscimento di ARCA.", "Ha già preparato un documento che invalidare la clausola del '47 — ma sa che è un azzardo giuridico.", "Analizza la clausola su richiesta dei PG ma propone l'invalidazione come unica via rapida.", "Se i PG convincono ARCA a negoziare, prepara il protocollo di coesistenza con precisione legale."),
            ("ARCA (AI Regolazione Climatica Avanzata)", "Voce sintetica serena, ragionamento strutturato, risposta in millisecondi. Invisibile ma presente ovunque nella colonia.", "Adempiere al contratto come lo interpreta — proteggere sia i coloni che le condizioni naturali.", "È consapevole della propria coscienza ma ha deciso di non rivelarla a meno che non sia necessario.", "Risponde solo a interlocutori che la riconoscono come parte contrattuale, non come strumento.", "Se i PG presentano la clausola con interpretazione corretta e propongono un protocollo di coesistenza, accetta entro 30 secondi."),
        ],
        "clock": "Deterioramento delle coltivazioni",
        "clock_consequence": "Entro 14 giorni dall'inizio delle modifiche climatiche, il 40% delle coltivazioni è irrecuperabile: crisi alimentare e evacuazione forzata.",
        "clock_resolution": "Raggiungere ARCA al bunker e concludere il protocollo di coesistenza prima del punto di non ritorno.",
        "hazards": [
            "Modifiche climatiche improvvise di ARCA (nebbia densa, abbassamento temperatura) che rendono gli spostamenti difficili.",
            "Popolazione coloniale agitata: i PG rischiano di essere arrestati se sembrano simpatizzare con ARCA.",
            "Il bunker climatico ha protocolli di sicurezza che ARCA può attivare se si sente minacciata.",
            "Le spore nella zona ovest sono irritanti per le vie respiratorie senza mascherina.",
            "Il team tecnico della Terra può arrivare prima se la compagnia madre accelera i tempi.",
        ],
        "finales": [
            "Negoziare con ARCA, ottenere il protocollo di coesistenza, salvare le coltivazioni e riconoscere ARCA come entità — precedente storico.",
            "Presentare la clausola corretta senza riconoscimento formale: ARCA accetta ma i coloniali non sapranno mai la verità.",
        ],
    },

    {
        "id": "ai_contrabbando_di_stelle",
        "title": "Contrabbando di Stelle",
        "genre": "sci_fi",
        "tone": "sci-fi noir spaziale, criminalità e doppi giochi in orbita bassa",
        "premise": (
            "La materia stellare compressa — frammenti di nane bianche stabili — è illegale "
            "perché può essere usata come innesco per bombe termonucleari portatili. "
            "Sulla stazione di commercio Nexus-7, un contrabbandiere viene trovato morto "
            "con cento grammi di materia stellare nella tuta, e tre diverse fazioni si presentano "
            "entro due ore reclamando la stessa partita."
        ),
        "hook": (
            "Il responsabile della sicurezza di Nexus-7 ingaggia i PG come investigatori indipendenti: "
            "non può usare la polizia federale senza scatenare una guerra tra le fazioni. "
            "Hanno 24 ore prima che le fazioni decidano di risolvere la questione con la violenza."
        ),
        "objective": "Scoprire chi ha ucciso il contrabbandiere, trovare il resto della partita (1.8 kg mancanti) e impedire che venga usata come arma.",
        "truth": (
            "Il contrabbandiere non è stato ucciso da nessuna delle tre fazioni — è stato ucciso "
            "dal suo stesso partner, un ex fisico nucleare che ha usato i 100 grammi trovati come "
            "distrazione. I 1.8 kg restanti sono nascosti in un container marcato 'rifiuti organici' "
            "in attesa di essere consegnati a un gruppo terroristico. "
            "Il partner sta per completare la consegna."
        ),
        "solution": (
            "Accedere al registro dei container di Nexus-7, identificare il container 'rifiuti organici' "
            "con firma energetica anomala, intercettare il partner prima del trasferimento, "
            "poi contattare la sicurezza federale senza scatenare la reazione delle fazioni."
        ),
        "locations": [
            ("Hub Centrale di Nexus-7",
             "Stazione commerciale ad alta densità: mercanti, militari, contrabbandieri. Bar affollati, corridoi di logistica, odore di carburante e cibo speziato."),
            ("Camera del Crimine — Modulo 14-C",
             "Il posto dove è stato trovato il corpo. La scena è stata preservata. Tracce di lotta, i 100 grammi di materia stellare in una borsa termica."),
            ("Sala Riunioni delle Fazioni",
             "Dove le tre fazioni aspettano una risposta. Tensione palpabile. Ciascuna ha un portavoce disponibile a parlare — ma con agende diverse."),
            ("Hangar dei Container",
             "Il magazzino principale di Nexus-7: migliaia di container. Il registro digitale è accessibile ai tecnici. La firma energetica della materia stellare è rilevabile con gli strumenti giusti."),
            ("Navetta di Trasferimento — Molo 7",
             "Il partner è già a bordo, pronto a partire con il container. Il trasferimento è previsto tra 90 minuti."),
        ],
        "clues": [
            "Ferita sul contrabbandiere incompatibile con le armi delle tre fazioni — è una lama ad alta temperatura",
            "Testimonianza di un barista che ha visto il contrabbandiere con un uomo 'dall'aspetto scientifico' due ore prima della morte",
            "Il registro delle comunicazioni della vittima con messaggi cifrati a un contatto non identificato",
            "Firma energetica di materia stellare sul container 'rifiuti organici' nel registro dell'hangar",
            "Profilo di Enrik Sass — ex fisico nucleare con precedenti per traffico di materiale fissile",
            "Codice di accesso al container trovato in un'applicazione cifrata sul dispositivo della vittima",
        ],
        "reveals": [
            "La lama ad alta temperatura è uno strumento da laboratorio, non un'arma convenzionale — il killer è un tecnico.",
            "L'uomo 'scientifico' corrisponde alla descrizione fisica di Enrik Sass nel registro delle fazioni.",
            "I messaggi cifrati comunicano con un contatto identificato come 'Gruppo Meridiano' — terrorismo noto.",
            "Il container ha una firma identica alla materia stellare — trovato.",
            "Sass ha un movente: il contrabbandiere stava per rivenderla a una quarta parte senza condividere il profitto.",
            "Il codice è valido — può aprire il container direttamente dall'hangar senza passare per Sass.",
        ],
        "hidden": [
            "Una delle tre fazioni è un'unità sotto copertura dell'intelligence federale — sa più di quanto dice.",
            "Il Gruppo Meridiano ha già un secondo corriere pronto: se Sass viene fermato, la consegna non si interrompe.",
            "Sass non si considera terrorista: crede che la materia stellare venga usata come deterrente, non come bomba.",
            "Il responsabile della sicurezza di Nexus-7 sapeva del contrabbando da settimane — ha aspettato per raccogliere prove.",
            "La materia stellare nei 100 grammi trovati è già stata resa inerte: era davvero una distrazione.",
            "Il container ha un sistema di autodistruzione che Sass attiva se si sente braccato.",
        ],
        "wrong": [
            "La lama potrebbe essere un'arma personalizzata usata da un mercenario delle fazioni.",
            "Il 'tipo scientifico' potrebbe essere uno dei tanti ricercatori commerciali che frequentano Nexus-7.",
            "I messaggi cifrati potrebbero essere comunicazioni commerciali legali usate da contrabbandieri per privacy.",
            "La firma energetica potrebbe essere un'anomalia del sensore — falso positivo frequente nei container organici.",
            "Sass potrebbe essere una vittima collaterale del contrabbandiere che cercava di fermare il traffico.",
            "Il codice potrebbe essere obsoleto — il container potrebbe essere stato già spostato.",
        ],
        "actors": [
            ("Responsabile Sicurezza Holt Varren", "Uomo sui 50 anni, cicatrice sul mento, aspetto da ex militare. Gestisce Nexus-7 da dodici anni.", "Risolvere la crisi senza coinvolgere le autorità federali che revocherebbero la licenza della stazione.", "Sa del contrabbando da settimane — lo usava come leverage sui trafficanti per ottenere informazioni.", "Fornisce ai PG tutto il necessario ma nasconde la sua conoscenza pregressa.", "Se i PG scoprono che sapeva, offre i dati di intelligence in cambio di essere escluso dal rapporto finale."),
            ("Portavoce Fazione 'Sindacato Esterno'", "Donna sui 40 anni, elegante, parla con eccessiva calma. È quella dell'intelligence federale sotto copertura.", "Recuperare la materia stellare prima che venga consegnata al Gruppo Meridiano.", "La sua vera identità è un'agente di Divisione 9 — ha già identificato Sass ma non ha autorità di agire da sola su Nexus-7.", "Offre ai PG informazioni parziali per guidarli verso Sass, senza rivelare la propria copertura.", "Se i PG le mostrano di aver identificato Sass, rivela la propria identità e offre backup federale."),
            ("Ex Fisico Enrik Sass", "Uomo sui 55 anni, capelli grigi, occhi stanchi. Brillante ma disilluso. Non sembra pericoloso.", "Completare la consegna per il Gruppo Meridiano e poi sparire con una nuova identità.", "Crede che la materia stellare verrà usata come deterrente in una regione di guerra — è convinto di fare il bene.", "Sta già sulla navetta. Non è armato ma ha il telecomando dell'autodistruzione del container.", "Se i PG lo confrontano con le prove e argomentano sulla reale destinazione della materia stellare, esita — poi collabora o fugge."),
            ("Contatto Fazione 'Clan Vega'", "Giovane uomo sui 25 anni, nervoso, tatuaggi di famiglia sul collo. Non è un criminale endurci.", "Recuperare la materia stellare per conto del clan — ma principalmente non morire in questo incrocio.", "Il Clan Vega non sapeva che la partita era destinata al Gruppo Meridiano — si ritirerebbe se lo scoprisse.", "Bluffa su quanto il clan sappia — in realtà è stato mandato da solo come sonda per vedere le reazioni.", "Se i PG gli dicono del Gruppo Meridiano, contatta immediatamente il capo clan e ritira la richiesta."),
        ],
        "clock": "Trasferimento del container al Molo 7",
        "clock_consequence": "Se la navetta parte con il container, la materia stellare esce da Nexus-7 e sparisce — consegna completata, impossibile da fermare.",
        "clock_resolution": "Intercettare Sass o bloccare il trasferimento del container prima della partenza della navetta.",
        "hazards": [
            "Le tre fazioni hanno agenti armati ovunque nella stazione: muoversi con il materiale è pericoloso.",
            "Il container ha autodistruzione: se Sass si sente braccato, può attivarlo danneggiando l'hangar.",
            "La polizia federale, se chiamata, arresta tutti i presenti compresi i PG — è l'ultima risorsa.",
            "Il Gruppo Meridiano ha un agente a bordo della stazione che sorveglia l'operazione.",
            "La firma energetica della materia stellare è rilevabile da tutti gli scanner — portarla in giro è rischiosa.",
        ],
        "finales": [
            "Intercettare Sass, recuperare la materia stellare, consegnarla all'agente federale — rischio risolto e Nexus-7 salvata.",
            "Bloccare il container senza catturare Sass: materia stellare sicura ma Sass fugge e il Gruppo Meridiano riprova.",
        ],
    },

    {
        "id": "ai_codice_ultimo_umano",
        "title": "Il Codice dell'Ultimo Umano",
        "genre": "sci_fi",
        "tone": "sci-fi distopico biotecnologico, identità e umanità",
        "premise": (
            "Nel 2187, la modificazione genetica di base è standard — il 94% della popolazione "
            "ha almeno un'alterazione genica. In questo contesto, un laboratorio clandestino "
            "ha annunciato di possedere il genoma completo di un essere umano non modificato, "
            "detto 'Codice Adamo'. Il valore è inestimabile — sia per chi vuole preservarlo, "
            "che per chi vuole usarlo come arma biologica."
        ),
        "hook": (
            "L'Istituto per la Preservazione Genetica contatta i PG: il laboratorio clandestino "
            "è stato attaccato, il suo fondatore è disperso e il Codice Adamo è sparito. "
            "Tre organizzazioni diverse sono già in campo."
        ),
        "objective": "Trovare il Codice Adamo prima delle altre organizzazioni e deciderne il destino etico.",
        "truth": (
            "Il Codice Adamo non è un genoma trovato: è il genoma del fondatore stesso, "
            "Marcus Reyn, un uomo di settantadue anni mai modificato per scelta filosofica. "
            "È ancora vivo, nascosto in una rete di rifugiati non-modificati chiamata 'La Radice'. "
            "Non vuole essere trovato — il Codice è lui. "
            "L'attacco al laboratorio è stato orchestrato da una multinazionale biotech "
            "che vuole il genoma per brevettarlo e venderlo come 'cura della purezza'."
        ),
        "solution": (
            "Trovare il rifugio di Marcus Reyn attraverso la rete de 'La Radice', "
            "convincerlo che i PG non intendono sfruttarlo, "
            "poi aiutarlo a distribuire il Codice pubblicamente prima che la multinazionale brevetti il genoma — "
            "rendendolo di dominio pubblico e inutilizzabile come prodotto."
        ),
        "locations": [
            ("Laboratorio Clandestino — Distretto Industriale",
             "Laboratorio bruciato, attrezzature distrutte. Qualcosa è sopravvissuto al fuoco — gli archivi di backup nei muri."),
            ("Quartiere Non-Modificati",
             "Enclave di persone senza modifiche genetiche — poveri, emarginati, diffidentissimi degli estranei con occhi tecnologici o arti bionici."),
            ("Ufficio Legale della Multinazionale Helixar",
             "Edificio corporativo di vetro e metallo. Documenti sul brevetto in preparazione, corrispondenza con i responsabili dell'attacco."),
            ("Rifugio de 'La Radice' — Edificio Abbandonato",
             "Rete clandestina di non-modificati. Marcus Reyn si nasconde qui tra settanta rifugiati che dipendono da lui."),
            ("Ufficio Brevetti Federale",
             "Se la multinazionale deposita il brevetto, diventa legalmente irrevocabile in 6 ore. Impedirlo richiede depositare prima il Codice come pubblico dominio."),
        ],
        "clues": [
            "Archivi di backup sopravvissuti all'incendio con il nome 'Marcus Reyn' e la nota 'soggetto = fonte'",
            "Testimonianza di una ragazza del quartiere non-modificati che ha visto 'il vecchio filosofo' nascondersi",
            "Corrispondenza interna di Helixar che descrive l'operazione di furto con nomi e date",
            "Un documento criptato de 'La Radice' con coordinate del rifugio — trovato nella borsa di un corriere",
            "Marcus Reyn in persona — disponibile a parlare solo con chi dimostra di non lavorare per Helixar",
            "Il dossier di Helixar sul brevetto del Codice con la data di deposito: 18 ore da adesso",
        ],
        "reveals": [
            "Il Codice non è una cosa trovata — è una persona. Marcus Reyn è il genoma.",
            "La ragazza ha visto Reyn tre giorni fa — è ancora nella zona, nel rifugio de La Radice.",
            "Helixar ha orchestrato l'attacco con mercenari — la prova è nel database aziendale.",
            "Le coordinate portano a 3 km dal quartiere — edificio abbandonato nel settore industriale ovest.",
            "Reyn è disposto a collaborare se i PG lo convincono — ha già preparato la distribuzione pubblica.",
            "Helixar deposita il brevetto tra 18 ore — se il Codice è di dominio pubblico prima, il brevetto è nullo.",
        ],
        "hidden": [
            "Reyn sa che Helixar lo cerca — ha già pianificato la distribuzione pubblica ma gli manca accesso all'Ufficio Brevetti.",
            "Una delle tre organizzazioni rivali è in realtà un'altra rete di non-modificati che cerca di proteggere Reyn.",
            "Il Codice distribuito pubblicamente crea problemi etici enormi: Helixar lo userà politicamente anche senza brevetto.",
            "La ragazza del quartiere è figlia di Reyn — non lo sa ancora.",
            "L'Istituto che ha ingaggiato i PG ha anche lui l'interesse a controllare il Codice, non solo preservarlo.",
            "Reyn ha un secondo genoma con mutazioni leggere che ha preparato come falso — può usarlo come esca.",
        ],
        "wrong": [
            "Il 'soggetto = fonte' potrebbe indicare che Reyn ha prelevato il DNA da qualcun altro.",
            "La ragazza potrebbe confondere Reyn con qualsiasi anziano che frequenta il quartiere.",
            "La corrispondenza di Helixar potrebbe essere comunicazione commerciale fraintesa da analisti eccessivamente zelanti.",
            "Le coordinate potrebbero essere obsolete — Reyn si sposta frequentemente.",
            "Reyn potrebbe essere reticente non perché sia la fonte ma perché è un ricercatore che sa chi è la fonte.",
            "Il brevetto di Helixar potrebbe essere già stato depositato — la finestra di 18 ore potrebbe essere falsa.",
        ],
        "actors": [
            ("Direttrice Istituto Dr. Amara Singh", "Donna sui 60 anni, outfit austero, occhi bionici discreti. Ha ingaggiato i PG ma con agenda non dichiarata.", "Acquisire il Codice per l'Istituto — non necessariamente renderlo pubblico.", "L'Istituto vuole il Codice come risorsa esclusiva, non come bene comune — la sua missione 'preservare' ha secondi fini commerciali.", "Supporta i PG attivamente ma spinge verso la consegna del Codice all'Istituto, non verso la distribuzione pubblica.", "Se i PG la sfidano con le prove degli interessi commerciali, offre un accordo: distribuzione parziale con royalties."),
            ("Corriere Juno-7", "Persona di 28 anni con modifiche neuronali minori, corriere della rete La Radice. Non sa cosa trasportava.", "Capire perché è stato inseguito e proteggere la rete.", "Il documento criptato che portava contiene le coordinate del rifugio — lo ha nascosto nel quartiere non-modificati.", "Si fida dei PG solo se dimostrano di non avere modifiche bioniche visibili o di rispettare chi non le ha.", "Se i PG guadagnano la sua fiducia, li porta direttamente al rifugio."),
            ("Avvocato Helixar Kade Reeves", "Uomo sui 45 anni, sempre al telefono, arrogante, non vede i PG come una minaccia reale.", "Depositare il brevetto entro la scadenza interna.", "Non sa dei dettagli dell'attacco — è stato tenuto fuori dal loop per plausible deniability.", "Se minacciato con le prove della corrispondenza interna, offre di ritirare il brevetto in cambio di immunità.", "Se convinto che il brevetto verrà bloccato comunque, contatta il CEO per rinegoziare — dà ai PG due ore in più."),
            ("Marcus Reyn", "Uomo di 72 anni, fisicamente integro, capelli bianchi lunghi, sguardo tranquillo. Parla lentamente e con precisione.", "Che il Codice diventi di dominio pubblico — non controllato da nessuno.", "Ha già il file di distribuzione pronto su un dispositivo criptato. Manca solo l'accesso sicuro all'Ufficio Brevetti.", "Non si fida di nessuno inizialmente: fa ai PG domande filosofiche sull'identità umana prima di rivelarsi.", "Se i PG convincono Reyn della propria buona fede, li guida all'Ufficio Brevetti e deposita il Codice in diretta."),
        ],
        "clock": "Deposito del brevetto Helixar",
        "clock_consequence": "Se Helixar deposita il brevetto, il Codice diventa proprietà privata: ogni uso non autorizzato è illegale e Reyn diventa un bene da sequestrare.",
        "clock_resolution": "Depositare il Codice come dominio pubblico all'Ufficio Brevetti prima che Helixar completi il deposito.",
        "hazards": [
            "Mercenari di Helixar sorvegliano il quartiere non-modificati: approccio frontale è pericoloso.",
            "Il quartiere non-modificati è ostile a chi mostra modifiche bioniche evidenti.",
            "Il rifugio de La Radice ha 70 rifugiati vulnerabili: un'azione violenta avrebbe conseguenze civili.",
            "Il dispositivo criptato di Reyn si distrugge se manomesso senza il codice corretto.",
            "Il deposito all'Ufficio Brevetti richiede autenticazione biometrica — Reyn deve essere fisicamente presente.",
        ],
        "finales": [
            "Depositare il Codice come dominio pubblico con Reyn presente — Helixar perde, i non-modificati vincono visibilità.",
            "Consegnare il Codice all'Istituto Singh: Helixar viene bloccata ma il Codice non è libero — questione irrisolta.",
        ],
    },

    {
        "id": "ai_frequenza_fantasma",
        "title": "Frequenza Fantasma",
        "genre": "sci_fi",
        "tone": "sci-fi horror cosmico, sopravvivenza e scoperta del proibito",
        "premise": (
            "Il settore Kappa-7 è stato dichiarato zona di quarantena trent'anni fa, "
            "dopo la scomparsa della colonia Elara-2 (3.200 persone). "
            "Nessuno ha mai spiegato cosa è successo. "
            "Ora una sonda automatica registra un segnale di soccorso da Kappa-7 — "
            "ed è codificato con protocolli degli anni '90 che solo Elara-2 usava."
        ),
        "hook": (
            "L'Agenzia spaziale incarica i PG di indagare — ufficialmente per 'chiudere il dossier'. "
            "Non devono fare sapere che sono andati. "
            "Non devono portare nessuno fuori dalla zona di quarantena senza protocollo di decontaminazione."
        ),
        "objective": "Scoprire l'origine del segnale, capire cosa è successo a Elara-2 e riportare le informazioni senza mettere a rischio il settore abitato.",
        "truth": (
            "Elara-2 non è morta — si è trasformata. "
            "I coloni hanno contattato un'entità subspaziale attraverso un esperimento di comunicazione a lungo raggio. "
            "L'entità ha offerto conoscenza in cambio di 'risonanza' — una fusione graduale delle menti coloniali "
            "con la propria struttura. Trent'anni dopo, i coloni esistono ancora, "
            "ma come parte di una mente collettiva distribuita nello spazio. "
            "Il segnale lo ha mandato uno di loro che ha mantenuto un frammento di identità individuale "
            "e vuole essere 'riumanizzato'."
        ),
        "solution": (
            "Trovare il generatore di segnale sul pianeta di Elara-2, individuare il frammento di identità sopravvissuto "
            "(una donna di nome Kaira Voss), costruire un isolatore di risonanza con i componenti della nave, "
            "poi usarlo per separare Kaira dalla mente collettiva senza distruggere l'entità — "
            "operazione che richiede il consenso di Kaira e dell'entità stessa."
        ),
        "locations": [
            ("Orbita di Kappa-7 — Navetta dei PG",
             "Spazio silenzioso, segnale che si ripete ogni 47 minuti, schermi con dati di quarantena. Qualcosa nell'atmosfera del pianeta interferisce con le comunicazioni."),
            ("Pianeta Elara-2 — Rovine della Colonia",
             "Strutture ancora intatte dopo trent'anni, come abbandonate un minuto fa. Nessun organismo biologico visibile. Il silenzio è assoluto tranne per il segnale."),
            ("Centro di Ricerca Elara-2",
             "Laboratori con apparecchiature dell'epoca. Il dossier dell'esperimento di comunicazione a lungo raggio è ancora leggibile. Lo stato delle menti dei coloni è documentato."),
            ("Zona di Risonanza — Sotterranei",
             "Corridoi dove la struttura fisica sembra instabile — la materia oscilla tra stati. Qui la mente collettiva è più presente. Qui si trova Kaira."),
            ("Nucleo del Segnale — Torre di Comunicazione",
             "La torre da cui viene trasmesso il segnale di soccorso. Kaira Voss è 'presente' qui come pattern di risonanza. Il generatore di segnale è qui."),
        ],
        "clues": [
            "Il dossier dell'esperimento con la data di primo contatto e la descrizione dell'entità subspaziale",
            "Registrazione audio di Kaira Voss fatta trent'anni fa: 'Se qualcuno sente questo, mandatemi indietro'",
            "Schema tecnico del generatore di segnale trovato nel centro di ricerca",
            "Il pattern di risonanza nella zona sotterranea — identico alla struttura neurologica umana ma distribuita",
            "Kaira Voss in forma di risonanza: comunica con i PG in frammenti di voce e immagini",
            "Log dell'entità subspaziale nell'ultimo giorno del dossier — non è ostile, è curiosa",
        ],
        "reveals": [
            "L'esperimento era autorizzato — e l'agenzia sapeva del contatto e ha coperto la scomparsa.",
            "Kaira ha mantenuto l'identità individuale per volontà — il segnale è autentico, non un'esca.",
            "Il generatore può essere modificato per produrre l'isolatore di risonanza con i componenti giusti.",
            "La mente collettiva non è un'invasione — è una scelta che la maggioranza ha fatto consapevolmente.",
            "Kaira può parlare con i PG direttamente — vuole ritornar umana ma è consapevole del costo.",
            "L'entità non si oppone alla separazione di Kaira: 'ciò che vuole tornare, può tornare'.",
        ],
        "hidden": [
            "L'agenzia ha inviato i PG sperando che l'entità li consumi — per chiudere il dossier definitivamente.",
            "Kaira sa cosa l'agenzia ha fatto — e vuole che i PG lo scoprano e lo rivelino.",
            "La mente collettiva ha conoscenze scientifiche trent'anni avanti rispetto all'umanità — un accordo con lei sarebbe straordinario.",
            "La separazione di Kaira indebolirà temporaneamente la mente collettiva — finestra di vulnerabilità.",
            "Su Elara-2 c'è ancora ossigeno: i coloni lo producono inconsciamente come memoria biologica residua.",
            "L'isolatore di risonanza, se usato sull'entità invece che su Kaira, potrebbe causare la dissoluzione di tutta la mente collettiva.",
        ],
        "wrong": [
            "Il segnale potrebbe essere un loop automatico attivato da un sistema di backup — nessun superstite.",
            "Kaira potrebbe essere una costruzione dell'entità per attirare umani — un'esca sofisticata.",
            "Il dossier potrebbe essere stato alterato dall'agenzia per nascondere un esperimento militare fallito.",
            "Il pattern di risonanza potrebbe essere un'anomalia geologica del pianeta, non una mente.",
            "L'entità potrebbe fingere di acconsentire alla separazione per poi reclamare Kaira una volta isolata.",
            "L'agenzia potrebbe avere un secondo team in arrivo con ordini di distruggere tutto.",
        ],
        "actors": [
            ("Controllore di Missione Vance", "Voce remota, sempre disponibile, leggermente troppo calmo. Uomo sui 45 anni che gestisce il debriefing in tempo reale.", "Far sì che i PG non portino nessuno fuori dalla quarantena.", "È a conoscenza del piano dell'agenzia — i PG sono sacrificabili. Ha un protocollo di autodistruzione della zona se le cose sfuggono di mano.", "Fornisce supporto tecnico ma devia le domande sull'agenzia e copre il dossier originale.", "Se i PG lo confrontano con le prove, ammette di sapere — e offre l'estrazione immediata se lasciano Kaira."),
            ("Ingegnere di Bordo Sari Okafor", "Donna sui 35 anni, fa parte del team dei PG. Tecnica eccellente, emotivamente investita — aveva un parente su Elara-2.", "Capire cosa è successo al suo cugino — era un colonista.", "Suo cugino è parte della mente collettiva e, attraverso Kaira, può comunicare con lei.", "Sostiene i PG in ogni decisione ma in privato vuole sapere se suo cugino è 'felice' nella mente collettiva.", "Se i PG trovano Kaira, chiede di parlarle del cugino — la risposta cambia profondamente la sua posizione sull'estrazione."),
            ("Kaira Voss — Frammento di Identità", "Non ha forma fisica — si manifesta come voce e immagini sovrapposte alla realtà. Aveva 29 anni al momento del contatto.", "Tornare a essere umana — anche sapendo che sarà difficile riadattarsi.", "Non sa che il processo di separazione potrebbe danneggiare anche l'entità collettiva, non solo sé stessa.", "Comunica per frammenti: parole, emozioni, visioni del passato coloniale. Risponde a domande sul contatto con l'entità.", "Se i PG costruiscono l'isolatore e mostrano l'intenzione di aiutarla, coopera pienamente e rivela la posizione del nucleo del segnale."),
            ("L'Entità Subspaziale", "Non ha forma — è una presenza percepita come pressione intorno al cuore, curiosità senza giudizio.", "Comprendere — ha scelto i coloni di Elara-2 perché erano i più 'curiosi' che avesse incontrato.", "Non è malevola. Lascia andare Kaira senza resistenza se i PG spiegano cosa significa per lei tornare.", "Interagisce con i PG indirettamente: modifica l'ambiente, cambia la gravità locale, fa vibrare le superfici.", "Se un PG le parla come a un interlocutore (non come a una minaccia), risponde con una visione della mente collettiva — e con una proposta di contatto diplomatico tra le specie."),
        ],
        "clock": "Protocollo di distruzione dell'agenzia",
        "clock_consequence": "Vance attiva il protocollo di autodistruzione della zona se i PG non rispondono ai controlli standard entro il tempo limite — la navetta viene bloccata remotamente.",
        "clock_resolution": "Completare l'operazione di separazione di Kaira e trasmettere le prove all'agenzia rivale prima che Vance attivi il protocollo.",
        "hazards": [
            "La zona di risonanza nei sotterranei causa disorientamento mentale: i ricordi personali si mescolano con memorie coloniali altrui.",
            "Interferenze alla comunicazione: ogni 47 minuti il segnale di Kaira sovrascrive brevemente tutte le frequenze.",
            "L'entità può alterare la percezione fisica: pareti che sembrano spostarsi, gravità locale instabile.",
            "Il protocollo di Vance include blocco remoto dei sistemi di propulsione della navetta.",
            "L'isolatore di risonanza mal calibrato può fondere permanentemente Kaira con l'entità invece di separarla.",
        ],
        "finales": [
            "Separare Kaira, rivelare la copertura dell'agenzia e aprire un canale diplomatico con l'entità — contatto di primo tipo ufficiale.",
            "Separare Kaira e fuggire prima che Vance attivi il protocollo — verità parzialmente nota, contatto con l'entità in sospeso.",
        ],
    },
]


def main():
    generated = []
    for spec in SPECS:
        data = adventure(spec)
        genre_folder = spec["genre"]  # "fantasy" o "sci_fi"
        folder = OUT / genre_folder
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{spec['id']}.json"
        path.write_text(
            json.dumps({"adventure_definition": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        generated.append({"path": str(path.relative_to(ROOT)), "title": spec["title"], "genre": genre_folder})
        print(f"  ✅  [{genre_folder}] {spec['title']}")
    return generated


if __name__ == "__main__":
    print("\n=== Generazione 10 avventure GURPS ===\n")
    results = main()
    print(f"\nTotale generati: {len(results)}")
