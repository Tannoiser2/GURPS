"""
Adventure Templates — Predefined minimal adventure skeletons.

Each template is a dict compatible with compile_from_raw_structure(raw, ...).
Templates are complete enough to pass the adventure_doctor audit.
"""

from typing import Dict, List

ADVENTURE_TEMPLATES: List[Dict] = [
    # ── 1. Investigation Village ────────────────────────────────────────────────
    {
        "id": "investigation_village",
        "title": "Il Segreto del Mulino",
        "genre": "investigation",
        "premise": (
            "Un mugnaio è stato trovato morto nel suo mulino alla periferia del villaggio di Briarton. "
            "Le autorità locali vogliono chiudere il caso come incidente, ma i segni sul corpo "
            "raccontano una storia diversa. Qualcuno nel villaggio sa la verità, e ha tutto l'interesse "
            "a seppellirla insieme al mugnaio."
        ),
        "hidden_truth": (
            "Il mugnaio aveva scoperto che il sindaco stava dirottando fondi del villaggio verso "
            "una gilda criminale. Quando ha minacciato di rivelare tutto, il sindaco ha ingaggiato "
            "uno scagnozzo locale per farlo tacere."
        ),
        "threat_description": (
            "Il sindaco sta cercando di distruggere le prove e far fuggire il suo complice. "
            "Ogni turno perso avvicina la fuga del colpevole e il depistaggio delle prove."
        ),
        "win_condition": (
            "Raccogliere prove sufficienti contro il sindaco e portarle a un'autorità esterna "
            "oppure smascherarlo pubblicamente davanti ai testimoni del villaggio."
        ),
        "initial_hook": (
            "I personaggi arrivano a Briarton la mattina dopo la morte del mugnaio. "
            "La piazza è insolitamente silenziosa. Un ragazzo li avvicina di corsa: "
            "'Siete voi gli investigatori? Mio padre non è morto per un incidente. "
            "Per favore, aiutatemi — nessuno qui vuole sentire la verità.'"
        ),
        "actors": [
            {
                "id": "npc_sindaco",
                "name": "Sindaco Aldric Vorn",
                "role": "villain",
                "goal": "Distruggere le prove e far fuggire il complice prima che la verità emerga",
                "secret": "Ha ordinato l'omicidio del mugnaio per proteggere il suo schema corruttivo",
                "location_id": "loc_municipio",
                "attitude": "cordiale e collaborativo in superficie, disperatamente ansioso sotto",
                "npc_agenda": "Usare l'autorità istituzionale per bloccare l'indagine",
                "agenda_pressure": 8,
                "pressure_response": {
                    "low": "Offre cooperazione formale e accesso limitato alle carte comunali",
                    "medium": "Cerca di screditare i PG come disturbatori forestieri",
                    "high": "Tenta di far arrestare i PG per 'interferenza' con le autorità",
                    "extreme": "Fugge o confessa parzialmente cercando di negoziare l'impunità"
                },
                "reaction_table": {
                    "se_minacciato": "Invoca l'autorità legale e minaccia conseguenze formali",
                    "se_i_pg_hanno_prove": "Cerca di corrompere o intimidire i PG perché lascino perdere",
                    "se_alleato": "Finge collaborazione mentre continua a depistare",
                    "se_smascherato_pubblicamente": "Crolla e tenta di scappare o negoziare"
                },
                "current_plan": "Contattare il complice e organizzarne la fuga entro due giorni",
                "fallback_plan": "Incolpare il complice di tutto e presentarsi come vittima"
            },
            {
                "id": "npc_complice",
                "name": "Bran il Cacciatore",
                "role": "antagonist",
                "goal": "Fuggire dal villaggio con il pagamento ricevuto per l'omicidio",
                "secret": "È l'assassino materiale del mugnaio — ha ancora l'arma del delitto nascosta",
                "location_id": "loc_foresta",
                "attitude": "evitante, nervoso, ostile se avvicinato",
                "npc_agenda": "Raccogliere i suoi averi e scomparire prima di essere trovato",
                "agenda_pressure": 7,
                "pressure_response": {
                    "low": "Evita i PG e nega ogni coinvolgimento",
                    "medium": "Scompare nella foresta e attende istruzioni dal sindaco",
                    "high": "Attacca i PG se sente di essere in trappola",
                    "extreme": "Scappa o rivela il coinvolgimento del sindaco in cambio di protezione"
                },
                "reaction_table": {
                    "se_minacciato": "Aggredisce o fugge, a seconda dei numeri",
                    "se_i_pg_hanno_prove": "Tenta di scappare immediatamente",
                    "se_alleato_del_sindaco": "Chiede più denaro e un piano di fuga",
                    "se_catturato": "Rivela tutto sul sindaco pur di ridurre la pena"
                },
                "current_plan": "Aspettare il via libera del sindaco, poi sparire nei boschi",
                "fallback_plan": "Scaricare tutta la colpa sul sindaco e consegnarsi in cambio di immunità"
            },
            {
                "id": "npc_figlio",
                "name": "Tobin Ashford",
                "role": "ally",
                "goal": "Ottenere giustizia per la morte del padre e proteggere la famiglia del mugnaio",
                "secret": "Sa che suo padre aveva trovato un libro mastro con i conti truccati del sindaco",
                "location_id": "loc_mulino",
                "attitude": "disperato, coraggioso, si fida dei PG se dimostrano buone intenzioni",
                "npc_agenda": "Guidare i PG verso le prove che il padre aveva nascosto",
                "pressure_response": {
                    "low": "Risponde alle domande con sincerità e condivide sospetti",
                    "medium": "Accompagna i PG al mulino e indica i nascondigli del padre",
                    "high": "Si espone pubblicamente per difendere i PG se minacciati",
                    "extreme": "Rischia la propria vita per consegnare le prove alle autorità esterne"
                },
                "reaction_table": {
                    "se_minacciato": "Chiede aiuto ai PG e li avverte del pericolo",
                    "se_i_pg_hanno_prove": "Li aiuta a trovare ulteriori conferme",
                    "se_tradito": "Si ritira e smette di cooperare",
                    "se_i_pg_vincono": "Porta una testimonianza pubblica definitiva"
                },
                "current_plan": "Trovare il libro mastro prima che il sindaco lo distrugga",
                "fallback_plan": "Fuggire con la madre dal villaggio se la situazione si fa pericolosa"
            },
            {
                "id": "npc_guardia",
                "name": "Guardia Holt",
                "role": "neutral",
                "goal": "Mantenere l'ordine nel villaggio e obbedire alle autorità locali",
                "secret": "Sospetta che il sindaco sia coinvolto ma ha troppa paura per agire",
                "location_id": "loc_municipio",
                "attitude": "professionale ma reticente, diviso tra dovere e paura",
                "npc_agenda": "Proteggere la propria posizione evitando di schierarsi",
                "pressure_response": {
                    "low": "Fornisce informazioni burocratiche di facciata",
                    "medium": "Avverte i PG di stare attenti 'per il loro bene'",
                    "high": "Disobbedisce agli ordini del sindaco se i PG lo convincono",
                    "extreme": "Testimonia contro il sindaco se ha garanzia di protezione"
                },
                "reaction_table": {
                    "se_minacciato_dal_sindaco": "Obbedisce, ma lascia indizi deliberati per i PG",
                    "se_i_pg_hanno_prove": "Cede informazioni cruciali in segreto",
                    "se_alleato": "Fornisce accesso a luoghi altrimenti chiusi",
                    "se_in_pericolo": "Chiede aiuto e si schiera apertamente con i PG"
                },
                "current_plan": "Tenere la testa bassa finché la situazione non si chiarisce",
                "fallback_plan": "Schierarsi con chi vince, portando prove della propria innocenza"
            }
        ],
        "clues": [
            {
                "id": "clue_impronte",
                "label": "Impronte di stivali da caccia",
                "type": "physical_evidence",
                "thread_id": "T1",
                "source_location": "loc_mulino",
                "reveals": "Qualcuno con stivali da caccia era presente al mulino la notte della morte",
                "immediate_information": "Nel fango vicino al mulino ci sono impronte pesanti di stivali chiodati da caccia, diverse da quelle del mugnaio",
                "hidden_implication": "Bran il Cacciatore usa questo tipo di stivali — le impronte portano verso la foresta",
                "possible_actions": ["Misurare le impronte", "Seguire le tracce verso la foresta", "Confrontarle con i piedi di Bran"]
            },
            {
                "id": "clue_libro_mastro",
                "label": "Libro mastro con conti truccati",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_mulino",
                "reveals": "Il mugnaio aveva documentato pagamenti irregolari tra il comune e una gilda criminale",
                "immediate_information": "Un piccolo libro nascosto nella macina del mulino contiene numeri e nomi in codice, con la firma del sigillo comunale",
                "hidden_implication": "Il mugnaio stava raccogliendo prove contro il sindaco da mesi — era vicino ad avere abbastanza materiale",
                "possible_actions": ["Decifrare i codici nel libro", "Mostrarlo a un esperto di contabilità", "Usarlo come prova davanti a testimoni"]
            },
            {
                "id": "clue_lettera_minaccia",
                "label": "Lettera non spedita",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_mulino",
                "reveals": "Il mugnaio aveva scritto una lettera alle autorità provinciali con le sue scoperte",
                "immediate_information": "Una lettera parzialmente scritta in un cassetto, indirizzata al governatore della provincia, con un resoconto della corruzione",
                "hidden_implication": "Il mugnaio è stato ucciso prima di poter spedire la lettera — il sindaco probabilmente sapeva di questa lettera",
                "possible_actions": ["Completare e spedire la lettera al governatore", "Usarla come elemento di pressione sul sindaco", "Mostrare la lettera alla guardia Holt"]
            },
            {
                "id": "clue_testimone_taberna",
                "label": "Testimonianza del taverniere",
                "type": "testimony",
                "thread_id": "T1",
                "source_location": "loc_taverna",
                "reveals": "Bran il Cacciatore e il sindaco si sono incontrati di nascosto la notte prima della morte",
                "immediate_information": "Il taverniere li ha visti uscire assieme dal retro della taverna intorno a mezzanotte — avevano l'aria di non voler essere visti",
                "hidden_implication": "Il sindaco ha ingaggiato Bran direttamente — c'è una connessione diretta tra i due",
                "possible_actions": ["Chiedere altri dettagli al taverniere", "Verificare l'alibi del sindaco per quella notte", "Confrontare questa testimonianza con quella della guardia"]
            },
            {
                "id": "clue_arma_nascosta",
                "label": "Martello insanguinato",
                "type": "physical_evidence",
                "thread_id": "T1",
                "source_location": "loc_foresta",
                "reveals": "L'arma del delitto è nascosta nel capanno di Bran nella foresta",
                "immediate_information": "Un martello pesante da fabbro, con tracce di sangue e capelli corrispondenti alla vittima, avvolto in un sacco nella legnaia di Bran",
                "hidden_implication": "Bran non è riuscito a disfarsene — è ancora nel panico e ha nascosto l'arma troppo vicino a casa",
                "possible_actions": ["Portare il martello come prova fisica", "Confrontare il sangue con la ferita della vittima", "Usarlo per ottenere una confessione da Bran"]
            },
            {
                "id": "clue_pagamento",
                "label": "Sacchetto di monete marcate",
                "type": "physical_evidence",
                "thread_id": "T2",
                "source_location": "loc_foresta",
                "reveals": "Bran ha ricevuto un pagamento consistente in monete con il sigillo del comune",
                "immediate_information": "Un sacchetto di monete d'argento con impressa la testa del sindaco — la valuta ufficiale del comune di Briarton",
                "hidden_implication": "Il sindaco ha usato fondi comunali per pagare l'assassino — questo rafforza il legame tra corruzione e omicidio",
                "possible_actions": ["Mostrare le monete come prova del movente", "Rintracciare il prelievo nei registri comunali", "Presentarle insieme al libro mastro"]
            },
            {
                "id": "clue_alibi_falso",
                "label": "Contraddizione nell'alibi del sindaco",
                "type": "contradiction",
                "thread_id": "T2",
                "source_location": "loc_municipio",
                "reveals": "Il sindaco ha dichiarato di essere a casa quella notte, ma la guardia lo ha visto uscire",
                "immediate_information": "Il sindaco afferma di non aver lasciato la residenza la sera dell'omicidio, ma la guardia Holt ha un registro che mostra diversamente",
                "hidden_implication": "Il sindaco sta mentendo attivamente — il falso alibi è prova della sua consapevolezza",
                "possible_actions": ["Confrontare il sindaco con il registro", "Chiedere alla guardia di testimoniare formalmente", "Usare la contraddizione come leva per far crollare il sindaco"]
            },
            {
                "id": "clue_nota_gilda",
                "label": "Nota in codice dalla gilda",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_municipio",
                "reveals": "Una comunicazione cifrata tra il sindaco e la gilda criminale che prova il loro accordo",
                "immediate_information": "Nascosta nel cassetto del sindaco, una lettera in un codice commerciale che elenca pagamenti e 'servizi resi' alla gilda",
                "hidden_implication": "La relazione tra sindaco e gilda è consolidata da mesi — l'omicidio è l'ultimo atto di una serie di illeciti",
                "possible_actions": ["Decifrare il codice con l'aiuto di un mercante", "Inviare la nota alle autorità provinciali", "Usarla come prova aggiuntiva contro il sindaco"]
            }
        ],
        "story_threads": [
            {
                "id": "T1",
                "title": "Chi ha ucciso il mugnaio?",
                "question": "Chi è il responsabile materiale dell'omicidio e dove si trova?",
                "true_answer": "Bran il Cacciatore, ingaggiato dal sindaco, si nasconde nel bosco",
                "required_clues": ["clue_impronte", "clue_arma_nascosta", "clue_testimone_taberna"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Identificare e localizzare l'assassino materiale, aprendo la via alla cattura e alla prova del mandante"
            },
            {
                "id": "T2",
                "title": "Chi ha ordinato l'omicidio e perché?",
                "question": "Chi è il mandante e quale segreto voleva proteggere?",
                "true_answer": "Il sindaco ha fatto uccidere il mugnaio per nascondere la sua corruzione con la gilda criminale",
                "required_clues": ["clue_libro_mastro", "clue_lettera_minaccia", "clue_pagamento", "clue_nota_gilda"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Esporre il sindaco e smantellare lo schema corruttivo che soffoca il villaggio"
            }
        ],
        "event_clocks": [
            {
                "id": "clock_fuga_bran",
                "label": "Fuga di Bran",
                "max_value": 6,
                "consequence": "Bran il Cacciatore fugge dal villaggio con le prove; il sindaco ha più tempo per depistare",
                "clock_type": "terminal_defeat",
                "resolution_condition": "I PG trovano e fermano Bran prima che riceva il segnale del sindaco",
                "discovery_hint": "Un'anziana del villaggio nota che il capanno del cacciatore è buio da due giorni — di solito lui accende il fuoco ogni sera",
                "steps": [
                    {"value": 1, "label": "Bran è nervoso", "effect": "Bran vende i suoi cani da caccia — prepara la partenza"},
                    {"value": 2, "label": "Bran contatta il sindaco", "effect": "Il sindaco e Bran si incontrano di nascosto per coordinare la fuga"},
                    {"value": 4, "label": "Bran raccoglie i suoi averi", "effect": "La legnaia di Bran viene svuotata — se i PG arrivano ora trovano il capanno quasi vuoto"},
                    {"value": 6, "label": "Bran è fuggito", "effect": "Bran scompare nella foresta; il sindaco dichiara di non sapere niente"}
                ],
                "ticks_per_failure": 2
            },
            {
                "id": "clock_distruzione_prove",
                "label": "Distruzione delle prove",
                "max_value": 4,
                "consequence": "Il sindaco distrugge il libro mastro e le note della gilda; le prove fisiche svaniscono",
                "clock_type": "escalation",
                "resolution_condition": "I PG recuperano il libro mastro e le note prima che il sindaco le bruci o le nasconda",
                "discovery_hint": "Un servo del municipio vede il sindaco bruciare dei documenti nel camino — di notte, quando il palazzo dovrebbe essere vuoto",
                "steps": [
                    {"value": 1, "label": "Il sindaco è allarmato", "effect": "Il sindaco ordina alla guardia di non far entrare nessuno nel municipio senza autorizzazione"},
                    {"value": 2, "label": "Prime prove distrutte", "effect": "I registri ufficiali delle transazioni vengono modificati o bruciati"},
                    {"value": 3, "label": "Depistaggio attivo", "effect": "Il sindaco accusa un mercante innocente dell'omicidio, sviando l'attenzione"},
                    {"value": 4, "label": "Prove principali distrutte", "effect": "Senza le note della gilda e il libro mastro, le prove sono solo testimoniali"}
                ],
                "ticks_per_failure": 1
            }
        ],
        "locations": [
            {
                "id": "loc_mulino",
                "name": "Il Vecchio Mulino",
                "description": "Un mulino ad acqua sul bordo del ruscello, ora silenzioso. L'interno odora di farina e qualcosa di ferroso. Le pale girano ancora, ma nessuno le ferma."
            },
            {
                "id": "loc_municipio",
                "name": "Municipio di Briarton",
                "description": "Un edificio di pietra con la bandiera del comune. L'ufficio del sindaco è al primo piano, con una grande scrivania di mogano piena di carte in ordine sospetto."
            },
            {
                "id": "loc_taverna",
                "name": "La Taverna del Cervo",
                "description": "Il centro della vita sociale di Briarton. Il taverniere conosce tutti e tutto — se ha visto qualcosa, parlerà con la giusta persuasione."
            },
            {
                "id": "loc_foresta",
                "name": "Bosco e Capanno di Bran",
                "description": "Un sentiero tra i pini porta a un capanno isolato. Attrezzi da caccia, trappole e un odore di tabacco fresco. Qualcuno è stato qui di recente."
            },
            {
                "id": "loc_casa_mugnaio",
                "name": "Casa del Mugnaio",
                "description": "Una casetta accanto al mulino, ora silenziosa. La moglie e il figlio del mugnaio ricevono i PG con speranza negli occhi e paura nel cuore."
            }
        ]
    },

    # ── 2. Dungeon Escape ───────────────────────────────────────────────────────
    {
        "id": "dungeon_escape",
        "title": "Fuga dalle Catene di Ferro",
        "genre": "dungeon",
        "premise": (
            "I personaggi si risvegliano in una cella sotterranea senza ricordare come ci sono finiti. "
            "Le pareti trasudano umidità, si sentono passi pesanti in lontananza, e qualcuno fuori "
            "sta chiudendo a chiave un portone. Il tempo stringe: i carcerieri tornano tra poche ore "
            "e i PG devono trovare una via d'uscita attraverso un dedalo di dungeon sorvegliato."
        ),
        "hidden_truth": (
            "I personaggi sono stati catturati da un signore locale che li ha scambiati per spie. "
            "Il vero traditore è il suo fidato consigliere, che ha incastrato i PG per distogliere "
            "l'attenzione da sé. L'uscita dal dungeon è sorvegliata dal consigliere stesso."
        ),
        "threat_description": (
            "I carcerieri faranno il giro di ispezione. Ogni ritardo aumenta il rischio di essere "
            "riscoperti, e le prigioni più profonde non hanno via d'uscita."
        ),
        "win_condition": (
            "Raggiungere l'uscita del dungeon, portando con sé almeno una prova dell'innocenza dei PG "
            "o del tradimento del consigliere."
        ),
        "initial_hook": (
            "Il tonfo di un pesante chiavistello vi sveglia. Luce di torcia filtra da sotto la porta. "
            "Una voce rauca fuori: 'Ispezione tra tre ore. Se si lamentano, mandate a chiamarmi.' "
            "Passi che si allontanano. Siete in cella, i vostri equipaggiamenti sono spariti, "
            "e da qualche parte nel buio sentite un'altra persona respirare."
        ),
        "actors": [
            {
                "id": "npc_prigioniero",
                "name": "Marta la Contrabbandiera",
                "role": "ally",
                "goal": "Fuggire dal dungeon e far saltare il sistema corrotto che l'ha intrappolata",
                "secret": "Conosce una via d'uscita segreta, ma richiede una chiave che è in mano al carceriere capo",
                "location_id": "loc_cella_prigionieri",
                "attitude": "diffidente ma pragmatica — collabora se i PG dimostrano competenza",
                "npc_agenda": "Usare i PG come diversivo per raggiungere la via di fuga",
                "pressure_response": {
                    "low": "Osserva i PG e valuta se fidarsi",
                    "medium": "Condivide informazioni sul layout del dungeon",
                    "high": "Guida attivamente i PG verso la via d'uscita",
                    "extreme": "Si sacrifica per coprire la fuga degli altri"
                },
                "reaction_table": {
                    "se_minacciata": "Si chiude e nega tutto — ha imparato a non fidarsi di nessuno",
                    "se_i_pg_la_aiutano": "Rivela la via segreta e condivide tutte le informazioni che ha",
                    "se_tradita": "Si separa dal gruppo e cerca una via solitaria",
                    "se_in_pericolo": "Combatte con sorprendente efficacia — sa il fatto suo"
                },
                "current_plan": "Aspettare il momento giusto per usare la via segreta del dungeon",
                "fallback_plan": "Creare un incendio controllato come diversivo e scomparire nel caos"
            },
            {
                "id": "npc_carceriere",
                "name": "Gurk il Carceriere Capo",
                "role": "antagonist",
                "goal": "Mantenere i prigionieri sotto controllo e ottenere una promozione dal signore",
                "secret": "È stato pagato dal consigliere per tenere i PG isolati e non indagare sui loro dossier",
                "location_id": "loc_sala_guardie",
                "attitude": "brutale, prevedibile, suscettibile alla corruzione",
                "npc_agenda": "Fare il suo lavoro senza complicazioni — detesta le sorprese",
                "agenda_pressure": 5,
                "pressure_response": {
                    "low": "Segue la routine, fa i giri di ispezione, non si preoccupa",
                    "medium": "Allerta le guardie quando sente rumori anomali",
                    "high": "Chiama i rinforzi e si mette alla testa della pattuglia",
                    "extreme": "Si barrica nell'ufficio e chiama il signore del castello"
                },
                "reaction_table": {
                    "se_corrotto": "Accetta la bustarella e finge di non vedere — per un po'",
                    "se_minacciato": "Attacca immediatamente e chiama i rinforzi",
                    "se_ingannato": "Ci cascò la prima volta; la seconda diventa sospettoso",
                    "se_scopre_la_fuga": "Suona il campanello d'allarme generale"
                },
                "current_plan": "Fare l'ispezione di routine e poi andare a dormire",
                "fallback_plan": "Chiudersi nell'ufficio con la chiave maestra e aspettare rinforzi"
            },
            {
                "id": "npc_consigliere",
                "name": "Consigliere Edwyn Pale",
                "role": "villain",
                "goal": "Assicurarsi che i PG non escano mai dal dungeon e non rivelino le sue trame",
                "secret": "Ha incastrato i PG con false accuse per nascondere il suo tradimento al signore",
                "location_id": "loc_uscita",
                "attitude": "presente come 'supervisore della sicurezza' — sembra premuroso ma è il vero nemico",
                "npc_agenda": "Controllare che i PG siano eliminati o rimangano imprigionati per sempre",
                "agenda_pressure": 9,
                "pressure_response": {
                    "low": "Osserva da lontano, manda le guardie al suo posto",
                    "medium": "Si presenta 'per verificare la situazione' e cerca di ostacolare i PG",
                    "high": "Ordina l'esecuzione immediata dei prigionieri in fuga",
                    "extreme": "Fugge dal castello prima che i PG possano accusarlo"
                },
                "reaction_table": {
                    "se_i_pg_hanno_prove": "Tenta di corrompere o eliminare i testimoni",
                    "se_minacciato": "Usa la sua posizione per far arrestare i PG di nuovo",
                    "se_smascherato": "Fugge o tenta di uccidere i PG prima che possano parlare",
                    "se_il_signore_viene_a_sapere": "Crolla e cerca di negoziare con false confessioni parziali"
                },
                "current_plan": "Convincere il signore che i PG devono essere giustiziati senza processo",
                "fallback_plan": "Fuggire con i fondi sottratti verso un territorio nemico"
            }
        ],
        "clues": [
            {
                "id": "clue_mappa_dungeon",
                "label": "Mappa graffita sul muro",
                "type": "location_detail",
                "thread_id": "T1",
                "source_location": "loc_cella_prigionieri",
                "reveals": "Qualcuno ha inciso una mappa parziale del dungeon sulla parete della cella",
                "immediate_information": "Graffiti sul mattone: un labirinto schematico con una X segnata su quello che sembra un passaggio secondario",
                "hidden_implication": "La mappa è vecchia ma accurata — qualcuno che era qui prima conosceva una via d'uscita",
                "possible_actions": ["Copiare la mappa", "Seguire il percorso indicato", "Mostrare la mappa a Marta per conferme"]
            },
            {
                "id": "clue_chiave_segreta",
                "label": "Chiave nascosta nella cella",
                "type": "physical_evidence",
                "thread_id": "T1",
                "source_location": "loc_cella_prigionieri",
                "reveals": "Qualcuno ha nascosto una chiave piccola sotto una pietra allentata del pavimento",
                "immediate_information": "Una chiave di ferro arrugginita, troppo piccola per la serratura della cella ma compatibile con qualcosa di più sottile",
                "hidden_implication": "Apre il passaggio segreto — Marta la riconosce immediatamente se la vedono",
                "possible_actions": ["Mostrare la chiave a Marta", "Testare la chiave su ogni serratura incontrata", "Usarla come oggetto di scambio con le guardie"]
            },
            {
                "id": "clue_documento_falso",
                "label": "Ordine di arresto falsificato",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_sala_guardie",
                "reveals": "L'ordine di arresto che ha portato alla cattura dei PG è una falsificazione con il sigillo del consigliere",
                "immediate_information": "Nell'ufficio del carceriere, un documento con il sigillo reale — ma la firma è diversa da quella del signore, assomiglia a quella del consigliere",
                "hidden_implication": "Il consigliere ha falsificato l'ordine usando il sigillo che gestisce normalmente per conto del signore",
                "possible_actions": ["Portare il documento fuori come prova", "Mostrarlo al signore del castello", "Usarlo come leva contro il consigliere"]
            },
            {
                "id": "clue_testimonianza_guardia",
                "label": "Guardia disillusa",
                "type": "testimony",
                "thread_id": "T2",
                "source_location": "loc_corridoio",
                "reveals": "Una giovane guardia sa che i PG sono stati arrestati su ordine del consigliere, non del signore",
                "immediate_information": "Una guardia che fa il turno di notte, annoiata e infelice, se trattata con rispetto rivela che 'il consigliere è venuto personalmente a ordinare l'arresto — non il signore'",
                "hidden_implication": "La guardia è una testimone oculare dell'abuso di potere del consigliere e potrebbe deporre",
                "possible_actions": ["Convincerla a deporre davanti al signore", "Chiederle di aprire una porta", "Scoprire dove si trova il consigliere"]
            },
            {
                "id": "clue_rotta_fuga",
                "label": "Condotto di areazione dimenticato",
                "type": "location_detail",
                "thread_id": "T1",
                "source_location": "loc_magazzino",
                "reveals": "Un vecchio condotto di areazione collega il magazzino all'esterno del castello",
                "immediate_information": "Dietro le casse del magazzino, una grata arrugginita copre un tunnel stretto ma percorribile — l'aria fresca che viene da lì non mente",
                "hidden_implication": "È la via d'uscita che Marta conosce — la chiave piccola apre il lucchetto della grata",
                "possible_actions": ["Usare la chiave sulla grata", "Strisciare attraverso il condotto", "Inviare qualcuno in avanscoperta"]
            }
        ],
        "story_threads": [
            {
                "id": "T1",
                "title": "Come uscire dal dungeon",
                "question": "Qual è la via d'uscita e come raggiungerla senza essere catturati?",
                "true_answer": "Il condotto di areazione nel magazzino è l'uscita — serve la chiave nascosta nella cella e la cooperazione di Marta",
                "required_clues": ["clue_mappa_dungeon", "clue_chiave_segreta", "clue_rotta_fuga"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Trovare il percorso verso l'uscita e le risorse per percorrerlo"
            },
            {
                "id": "T2",
                "title": "Chi ci ha messo qui e perché",
                "question": "Chi ha falsificato l'ordine di arresto e con quale scopo?",
                "true_answer": "Il consigliere Edwyn Pale ha incastrato i PG per nascondere il suo tradimento",
                "required_clues": ["clue_documento_falso", "clue_testimonianza_guardia"],
                "minimum_clues_to_deduce": 1,
                "payoff": "Uscire non solo fisicamente ma anche portando le prove per scagionarsi e incolpare il vero traditore"
            }
        ],
        "event_clocks": [
            {
                "id": "clock_ispezione",
                "label": "Ispezione dei Carcerieri",
                "max_value": 4,
                "consequence": "I carcerieri trovano la cella aperta e scattano l'allarme generale — ogni guardia del dungeon è in stato di allerta",
                "clock_type": "escalation",
                "resolution_condition": "I PG raggiungono il condotto di areazione o neutralizzano il carceriere capo",
                "discovery_hint": "Lontano, il suono di chiavi che tintinnano si avvicina a intervalli regolari",
                "steps": [
                    {"value": 1, "label": "Passi in lontananza", "effect": "Il carceriere capo inizia il giro, partendo dal livello superiore"},
                    {"value": 2, "label": "Rumori nel corridoio vicino", "effect": "Il carceriere è al piano dei PG — ogni rumore rischia di attirare la sua attenzione"},
                    {"value": 3, "label": "Il carceriere è nelle vicinanze", "effect": "Gurk è a poche celle di distanza — i PG devono nascondersi o agire"},
                    {"value": 4, "label": "Scoperta", "effect": "Gurk trova la cella vuota e suona il campanello — allarme generale"}
                ],
                "ticks_per_failure": 1
            },
            {
                "id": "clock_ordine_esecuzione",
                "label": "Ordine di Esecuzione",
                "max_value": 6,
                "consequence": "Il consigliere convince il signore a ordinare l'esecuzione immediata dei prigionieri",
                "clock_type": "terminal_defeat",
                "resolution_condition": "I PG escono dal dungeon o portano il documento falsificato al signore",
                "discovery_hint": "Una guardia mormora a un'altra: 'Il consigliere è dal signore da stamattina... non hanno un'aria buona'",
                "steps": [
                    {"value": 2, "label": "Il consigliere pressa il signore", "effect": "Il signore inizia a prendere in considerazione la richiesta del consigliere"},
                    {"value": 4, "label": "Il signore è quasi convinto", "effect": "Un messaggero scende al dungeon per 'verificare i prigionieri'"},
                    {"value": 6, "label": "Ordine firmato", "effect": "Il boia scende. I PG hanno un'ultima chance di mostrare le prove o combattere"}
                ],
                "ticks_per_failure": 1
            },
            {
                "id": "clock_rinforzi",
                "label": "Arrivo dei Rinforzi",
                "max_value": 3,
                "consequence": "Rinforzi bloccano il percorso verso il condotto — l'uscita diventa quasi impossibile",
                "clock_type": "escalation",
                "resolution_condition": "I PG raggiungono il condotto prima che i rinforzi blocchino il corridoio",
                "discovery_hint": "Da sopra, il rumore di cavalieri che entrano nel cortile del castello",
                "steps": [
                    {"value": 1, "label": "Cavalieri nell'atrio", "effect": "I nuovi arrivati ricevono il briefing dal consigliere — aggiungono guardie extra al dungeon"},
                    {"value": 2, "label": "Pattuglie doppiate", "effect": "I corridoi verso il magazzino sono presidiati da due guardie invece di una"},
                    {"value": 3, "label": "Blocco totale", "effect": "Ogni uscita è sorvegliata — i PG devono creare un diversivo o combattere un'uscita"}
                ],
                "ticks_per_failure": 1
            }
        ],
        "locations": [
            {
                "id": "loc_cella_prigionieri",
                "name": "Cella dei Prigionieri",
                "description": "Una cella 3x4 metri con paglia marcia sul pavimento. Le pareti di pietra mostrano graffiti di precedenti occupanti. Una finestrella in alto lascia passare poco aria ma niente luce."
            },
            {
                "id": "loc_corridoio",
                "name": "Corridoio Principale",
                "description": "Un lungo corridoio fiancheggiato da torce a intermittenza. Ogni cinquanta passi una svolta, ogni cento metri una guardia sonnacchiosa."
            },
            {
                "id": "loc_sala_guardie",
                "name": "Sala delle Guardie",
                "description": "La sala dove le guardie si alternano. Un tavolo con carte, cibo e la scatola delle chiavi. L'ufficio di Gurk è sul fondo, con la sua grande chiave che pende dalla cintura."
            },
            {
                "id": "loc_magazzino",
                "name": "Magazzino del Dungeon",
                "description": "Casse di provviste e attrezzatura ammassate disordinatamente. In fondo, quasi invisibile tra i rifiuti, la grata del vecchio condotto di areazione."
            },
            {
                "id": "loc_uscita",
                "name": "Portone d'Uscita",
                "description": "Il portone principale del dungeon, pesante e sbarrato. Il consigliere si aggira spesso da queste parti, 'supervisionando' la sicurezza."
            }
        ]
    },

    # ── 3. Heist ────────────────────────────────────────────────────────────────
    {
        "id": "heist",
        "title": "La Volta di Diamante",
        "genre": "heist",
        "premise": (
            "Una banca privata custodisce l'unico documento che può scagionare un innocente "
            "condannato a morte. La volta è protetta da tre livelli di sicurezza, sei guardie "
            "e un sistema di allarme all'avanguardia. I PG hanno tre giorni per pianificare, "
            "infiltrarsi ed uscire puliti — oppure la voce sbagliata arriva alle persone sbagliate."
        ),
        "hidden_truth": (
            "Il direttore della banca è complice nella messa in scena che ha condannato l'innocente. "
            "Il documento che i PG cercano prova non solo l'innocenza della vittima ma anche "
            "la colpevolezza del direttore stesso — che farà di tutto per impedirne il recupero."
        ),
        "threat_description": (
            "Il direttore sa che qualcuno sta girando attorno alla banca. Ogni indiscrezione "
            "dei PG accelera le sue contromosse: spostare il documento, aumentare la sicurezza, "
            "o far sparire le prove in modo permanente."
        ),
        "win_condition": (
            "Recuperare il documento dalla volta e portarlo a un avvocato indipendente "
            "o a un giornalista fidato, senza essere identificati come autori del colpo."
        ),
        "initial_hook": (
            "Una donna anziana con gli occhi rossi vi consegna una busta. Dentro: una foto "
            "di suo figlio in catene, e una nota scritta a mano. 'Sono rimaste 72 ore. "
            "Sapete dove guardare. Avete quello che serve. Vi prego.' Firma: Elena Varos. "
            "La data dell'esecuzione è stampigliata sull'angolo della foto."
        ),
        "actors": [
            {
                "id": "npc_direttore",
                "name": "Direttore Kasimir Vorek",
                "role": "villain",
                "goal": "Impedire il recupero del documento e far ricadere la colpa di qualsiasi furto su altri",
                "secret": "Ha manipolato le prove per incastrare Varos, con il documento nella volta come assicurazione sulla vita",
                "location_id": "loc_ufficio_direttore",
                "attitude": "impeccabile, autoritario, apparentemente incorruttibile",
                "npc_agenda": "Proteggere se stesso aumentando la sicurezza e spostando il documento",
                "agenda_pressure": 9,
                "pressure_response": {
                    "low": "Ordina una revisione di routine della sicurezza",
                    "medium": "Assume investigatori privati per scoprire chi sta curiosando",
                    "high": "Sposta il documento in un luogo segreto esterno alla banca",
                    "extreme": "Fa distruggere il documento e fugge con i fondi della banca"
                },
                "reaction_table": {
                    "se_minacciato": "Chiama le autorità e accusa i PG di estorsione",
                    "se_i_pg_hanno_il_documento": "Nega l'autenticità e cerca di far sequestrare le prove",
                    "se_smascherato": "Cerca di negoziare scambiando prove su crimini altrui",
                    "se_catturato": "Ammette tutto in cambio di immunità, tradendo i suoi complici"
                },
                "current_plan": "Assumere investigatori privati e aumentare la sorveglianza della banca",
                "fallback_plan": "Spostare il documento fuori dalla banca in un nascondiglio personale"
            },
            {
                "id": "npc_responsabile_sicurezza",
                "name": "Capitano Zara Velt",
                "role": "antagonist",
                "goal": "Fare il suo lavoro con professionalità e proteggere la banca da qualsiasi intrusione",
                "secret": "Sospetta che il direttore sia corrotto ma non ha prove — obbedisce agli ordini per ora",
                "location_id": "loc_sala_controllo",
                "attitude": "professionale, metodica, rispettosa delle regole",
                "npc_agenda": "Implementare le nuove misure di sicurezza ordinate dal direttore",
                "agenda_pressure": 6,
                "pressure_response": {
                    "low": "Segue la routine, controlla i turni, verifica le telecamere",
                    "medium": "Aumenta i pattugliamenti e avvisa il direttore di anomalie",
                    "high": "Mette tutta la banca in lockdown e chiama la polizia",
                    "extreme": "Si schiera con i PG se capisce che il direttore è il vero criminale"
                },
                "reaction_table": {
                    "se_i_pg_la_convincono": "Può aiutare se ha prove concrete della corruzione del direttore",
                    "se_scopre_i_pg": "Arresta i PG e li consegna al direttore — poi alla polizia",
                    "se_il_direttore_la_tradisce": "Si rivolta contro di lui e aiuta i PG",
                    "se_il_documento_emerge": "Apre una propria indagine interna sulla banca"
                },
                "current_plan": "Aggiornare il protocollo di sicurezza per la notte",
                "fallback_plan": "In caso di intrusione, proteggere fisicamente il direttore e chiamare rinforzi"
            },
            {
                "id": "npc_informatore",
                "name": "Luca il Tecnico",
                "role": "ally",
                "goal": "Farsi pagare bene per le informazioni sul sistema di allarme della banca",
                "secret": "Ha installato lui stesso il sistema di allarme e conosce una backdoor che nessun altro sa",
                "location_id": "loc_retro_banca",
                "attitude": "venale ma affidabile se pagato adeguatamente",
                "npc_agenda": "Monetizzare le sue conoscenze senza esporsi troppo",
                "pressure_response": {
                    "low": "Vende informazioni generali sul layout della banca",
                    "medium": "Rivela i codici del sistema di allarme per il prezzo giusto",
                    "high": "Accompagna i PG durante il colpo in cambio di una quota del bottino",
                    "extreme": "Sacrifica la propria copertura per salvare i PG in caso di emergenza"
                },
                "reaction_table": {
                    "se_pagato_bene": "Consegna le informazioni complete e oneste",
                    "se_minacciato": "Scompare e vende le informazioni alla polizia",
                    "se_tradito": "Contatta il direttore e rivela i piani dei PG",
                    "se_in_pericolo": "Si nasconde finché la situazione si calma"
                },
                "current_plan": "Aspettare che i PG tornino con i soldi promessi",
                "fallback_plan": "Sparire se sente che qualcosa va storto"
            },
            {
                "id": "npc_guardia_corrompibile",
                "name": "Guardia Petrov",
                "role": "neutral",
                "goal": "Guadagnare abbastanza per pagare i debiti di gioco che lo mettono in pericolo",
                "secret": "Deve soldi a degli usurai e sta valutando offerte provenienti da qualsiasi direzione",
                "location_id": "loc_ingresso_banca",
                "attitude": "nervoso, trasandato, si guarda le spalle",
                "npc_agenda": "Trovare un modo rapido per sistemarsi economicamente",
                "pressure_response": {
                    "low": "Fa il suo lavoro meccanicamente, distratto dai suoi problemi",
                    "medium": "Accetta piccoli favori economici e chiude un occhio su cose minori",
                    "high": "Accetta di agevolare l'accesso in cambio di una cifra sostanziosa",
                    "extreme": "Se in pericolo, rivela tutto ai superiori pur di non passare guai"
                },
                "reaction_table": {
                    "se_corrotto": "Lascia aperta una porta di servizio o disabilita una telecamera",
                    "se_minacciato": "Si sente in trappola e fa quello che gli viene detto",
                    "se_catturato_dalla_polizia": "Racconta tutto in cambio di protezione",
                    "se_pagato_abbastanza": "Sparisce durante il turno critico"
                },
                "current_plan": "Valutare quanto può guadagnare prima che i debiti diventino un problema fisico",
                "fallback_plan": "Denunciare i PG alla polizia come auto-protezione se la situazione degrada"
            },
            {
                "id": "npc_avvocato",
                "name": "Avvocatessa Isra Morn",
                "role": "ally",
                "goal": "Scagionare il suo cliente innocente con prove reali prima della data dell'esecuzione",
                "secret": "Ha già contatti con un giudice che sarebbe disposto ad aprire un nuovo processo se arrivassero prove nuove",
                "location_id": "loc_studio_legale",
                "attitude": "professionale, determinata, prende rischi calcolati",
                "npc_agenda": "Ottenere il documento come prova principale per il ricorso",
                "pressure_response": {
                    "low": "Fornisce ai PG informazioni legali e copertura professionale",
                    "medium": "Prepara il ricorso in attesa delle prove",
                    "high": "Contatta il giudice amico e crea una finestra temporale per la presentazione",
                    "extreme": "Va a stampa e pubblica tutto quel che ha, document o no"
                },
                "reaction_table": {
                    "se_i_pg_portano_il_documento": "Deposita immediatamente la richiesta di nuovo processo",
                    "se_minacciata": "Non cede — ha già inviato copie delle sue note al giudice",
                    "se_tradita": "Usa i canali legali per proteggere i suoi clienti",
                    "se_in_pericolo": "Chiama i PG e si fa proteggere mentre lavora"
                },
                "current_plan": "Preparare il fascicolo del ricorso — le mancano solo le prove",
                "fallback_plan": "Andare a stampa con quello che ha se le prove non arrivano in tempo"
            },
            {
                "id": "npc_giornalista",
                "name": "Reporter Finn Rao",
                "role": "ally",
                "goal": "Pubblicare lo scoop del secolo sulle corruzioni del sistema giudiziario",
                "secret": "Ha già raccolto prove collaterali sulla corruzione del direttore — manca solo la prova fisica",
                "location_id": "loc_studio_legale",
                "attitude": "entusiasta, impulsivo, etico a modo suo",
                "npc_agenda": "Rompere la storia prima che qualcun altro lo faccia",
                "pressure_response": {
                    "low": "Segue la storia da lontano e raccoglie informazioni di contorno",
                    "medium": "Pubblica articoli allusivi che aumentano la pressione sul direttore",
                    "high": "Pubblica tutto quello che sa, nomi inclusi, se crede sia giusto",
                    "extreme": "Si espone in prima persona per proteggere le sue fonti"
                },
                "reaction_table": {
                    "se_i_pg_lo_contattano": "Offre protezione mediatica in cambio dello scoop in esclusiva",
                    "se_minacciato": "Pubblica immediatamente per proteggersi — la luce è la miglior difesa",
                    "se_tradito": "Ritira la protezione e cerca nuove fonti",
                    "se_il_documento_arriva": "Pubblica entro ore, proteggendo le fonti"
                },
                "current_plan": "Aspettare sviluppi e non bruciarsi con indiscrezioni premature",
                "fallback_plan": "Pubblicare un pezzo di contorno che prepara il terreno per la storia principale"
            }
        ],
        "clues": [
            {
                "id": "clue_planimetria",
                "label": "Planimetria della banca",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_archivio_comunale",
                "reveals": "La struttura esatta della banca, incluse le vie di servizio e la posizione della volta",
                "immediate_information": "I permessi di costruzione depositati in comune mostrano ogni stanza, ogni porta e ogni corridoio della banca",
                "hidden_implication": "C'è un condotto di ventilazione non segnato nei progetti più recenti — è stato aggiunto dopo, probabilmente senza autorizzazione",
                "possible_actions": ["Identificare i punti di accesso alternativi", "Segnare la posizione delle telecamere", "Pianificare il percorso ottimale"]
            },
            {
                "id": "clue_codici_allarme",
                "label": "Manuali del sistema di allarme",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_retro_banca",
                "reveals": "Il sistema di allarme ha una finestra di manutenzione di 90 secondi ogni sera alle 23:00",
                "immediate_information": "Luca mostra i manuali tecnici: c'è una procedura di reset automatico notturno che disabilita i sensori per 90 secondi",
                "hidden_implication": "Quei 90 secondi sono la finestra per entrare — ma bisogna già essere nel corridoio giusto prima che si apra",
                "possible_actions": ["Sincronizzare l'ingresso con la finestra di 90 secondi", "Identificare il corridoio di accesso alla volta", "Verificare con Luca se la backdoor è ancora attiva"]
            },
            {
                "id": "clue_corruzione_direttore",
                "label": "Transazioni sospette del direttore",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_ufficio_direttore",
                "reveals": "Il direttore ha ricevuto pagamenti consistenti dalla famiglia che ha fatto incastrare Varos",
                "immediate_information": "Estratti conto bancari privati del direttore, trovati nello studio durante una ricognizione, mostrano bonifici regolari da un'entità anonima",
                "hidden_implication": "I pagamenti coincidono con la data del processo — il direttore è stato pagato per custodire e non divulgare il documento",
                "possible_actions": ["Usare le transazioni come prova aggiuntiva", "Ricattare il direttore per ottenere accesso facilitato", "Consegnare le prove all'avvocatessa Morn"]
            },
            {
                "id": "clue_turni_guardie",
                "label": "Registro dei turni delle guardie",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_sala_controllo",
                "reveals": "I turni delle guardie hanno una sovrapposizione di 10 minuti tra le 22:45 e le 23:00",
                "immediate_information": "Durante la staffetta notturna, due guardie convergono sulla stessa zona mentre le altre tornano alla sala di controllo — c'è un punto cieco",
                "hidden_implication": "Petrov fa sempre il turno da 22:00 alle 02:00 — è lui la guardia più accessibile per una corruzione",
                "possible_actions": ["Sfruttare il punto cieco durante la staffetta", "Contattare Petrov per la corruzione", "Pianificare l'ingresso nel momento di minor sorveglianza"]
            },
            {
                "id": "clue_posizione_documento",
                "label": "Ricevuta di deposito",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_retro_banca",
                "reveals": "Il documento di Varos è in una cassetta di sicurezza specifica, numero 447, al terzo livello della volta",
                "immediate_information": "Luca, se pagato abbastanza, mostra una ricevuta di deposito dalla quale si evince la posizione esatta dell'oggetto",
                "hidden_implication": "La cassetta 447 è registrata sotto un nome in codice — se si conosce il nome, si può accedervi legalmente durante l'orario d'ufficio",
                "possible_actions": ["Accedere legalmente con il nome in codice", "Aprire fisicamente la cassetta durante il colpo", "Usare Luca come tecnico per forzare la cassetta"]
            },
            {
                "id": "clue_identita_falsa",
                "label": "Documenti di identità falsi",
                "type": "physical_evidence",
                "thread_id": "T1",
                "source_location": "loc_retro_banca",
                "reveals": "Un contatto di Luca può fornire documenti di identità che permettono di entrare in banca come personale tecnico",
                "immediate_information": "Luca conosce un falsario che può preparare credenziali da tecnico di manutenzione in 24 ore",
                "hidden_implication": "Il sistema della banca non verifica la lista del personale esterno — una chiamata al numero sbagliato non viene controllata",
                "possible_actions": ["Ottenere le credenziali false", "Entrare durante l'orario d'ufficio come tecnici", "Usare le credenziali per accedere alle aree riservate"]
            },
            {
                "id": "clue_debito_petrov",
                "label": "Documenti di debito di Petrov",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_ingresso_banca",
                "reveals": "Petrov deve soldi a degli usurai e cerca disperatamente una via d'uscita economica",
                "immediate_information": "Durante una sorveglianza, i PG vedono Petrov discutere nervosamente con due uomini in giacca — che gli mostrano dei documenti in modo minaccioso",
                "hidden_implication": "Petrov è vulnerabile — un'offerta economica adeguata lo renderebbe un alleato prezioso",
                "possible_actions": ["Offrire soldi a Petrov in cambio di cooperazione", "Usare i suoi debiti come leva per ottenere accesso", "Pagare i suoi debiti in anticipo come gesto di buona fede"]
            },
            {
                "id": "clue_schema_telecamere",
                "label": "Angoli morti delle telecamere",
                "type": "location_detail",
                "thread_id": "T1",
                "source_location": "loc_ingresso_banca",
                "reveals": "Il sistema di telecamere ha angoli morti significativi nel corridoio est e vicino all'accesso alla volta",
                "immediate_information": "Dopo ore di sorveglianza esterna, i PG identificano i movimenti delle telecamere — ci sono punti dove la copertura è assente per 15-20 secondi",
                "hidden_implication": "Combinando gli angoli morti con la finestra di 90 secondi del reset, c'è un percorso fattibile verso la volta",
                "possible_actions": ["Mappare il percorso attraverso gli angoli morti", "Sincronizzare i movimenti con i punti ciechi", "Usare un diversivo per distogliere le telecamere"]
            },
            {
                "id": "clue_piano_b",
                "label": "Accesso tetti",
                "type": "location_detail",
                "thread_id": "T1",
                "source_location": "loc_retro_banca",
                "reveals": "Il lucernario del tetto è accessibile dall'edificio adiacente ed è aperto per manutenzione programmata",
                "immediate_information": "Il tetto dell'edificio adiacente è collegato alla banca da un ponteggio di manutenzione — e il lucernario sopra la camera forte non ha sensori attivi",
                "hidden_implication": "È il piano B: se l'ingresso principale viene compromesso, il tetto offre un percorso alternativo verso la volta",
                "possible_actions": ["Usare il lucernario come via d'accesso principale", "Prepararlo come via di fuga d'emergenza", "Verificare se il ponteggio regge il peso"]
            },
            {
                "id": "clue_prove_direttore_2",
                "label": "Lettera del direttore al falsario",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_ufficio_direttore",
                "reveals": "Il direttore ha commissionato lui stesso la falsificazione dei documenti che hanno incastrato Varos",
                "immediate_information": "Una lettera senza firma ma con il timbro personale del direttore, nella quale si ordina la preparazione di 'prove documentali irrefutabili' contro Varos",
                "hidden_implication": "Il direttore è il mandante della messa in scena, non solo un complice — questa lettera, insieme al documento nella volta, basta per un processo",
                "possible_actions": ["Portare la lettera all'avvocatessa", "Usarla come leva sul direttore", "Combinarla con il documento della volta per una prova completa"]
            }
        ],
        "story_threads": [
            {
                "id": "T1",
                "title": "Come penetrare nella banca",
                "question": "Qual è il piano per entrare, raggiungere la volta ed uscire senza essere catturati?",
                "true_answer": "La finestra di 90 secondi + il punto cieco delle telecamere + la corruzione di Petrov formano un piano fattibile; il tetto è il piano B",
                "required_clues": ["clue_codici_allarme", "clue_schema_telecamere", "clue_turni_guardie"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Un piano completo per il colpo, con accesso alla volta e via di fuga pulita"
            },
            {
                "id": "T2",
                "title": "La verità sulla condanna di Varos",
                "question": "Chi ha fatto incastrare Varos e che prove esistono per scagionarlo?",
                "true_answer": "Il direttore Vorek ha orchestrato la messa in scena; il documento nella volta e la lettera nel suo ufficio lo provano",
                "required_clues": ["clue_corruzione_direttore", "clue_prove_direttore_2", "clue_posizione_documento"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Prove sufficienti per scagionare Varos e incriminare il direttore, rendendo il colpo non solo un furto ma un atto di giustizia"
            }
        ],
        "event_clocks": [
            {
                "id": "clock_esecuzione",
                "label": "Conto alla rovescia per l'esecuzione",
                "max_value": 6,
                "consequence": "Varos viene giustiziato — il documento serve ancora per il processo ai responsabili ma la finestra per salvarlo si chiude",
                "clock_type": "terminal_defeat",
                "resolution_condition": "I PG consegnano il documento all'avvocatessa Morn o al giudice entro il tempo",
                "discovery_hint": "I giornali riportano la data dell'esecuzione di Varos — mancano pochi giorni",
                "steps": [
                    {"value": 1, "label": "T-72 ore", "effect": "La notizia dell'esecuzione imminente è sui giornali — c'è ancora tempo"},
                    {"value": 2, "label": "T-48 ore", "effect": "L'avvocatessa fa il suo ultimo appello legale — viene respinto senza prove"},
                    {"value": 4, "label": "T-24 ore", "effect": "L'ultimo appello formale è esaurito — solo le prove fisiche possono fermare l'esecuzione"},
                    {"value": 6, "label": "T-0: Esecuzione", "effect": "Varos è giustiziato — i PG possono ancora usare le prove per punire i responsabili"}
                ],
                "ticks_per_failure": 1
            },
            {
                "id": "clock_allerta_sicurezza",
                "label": "Livello di allerta della banca",
                "max_value": 4,
                "consequence": "La banca entra in modalità di sicurezza massima — il colpo diventa quasi impossibile senza un piano completamente diverso",
                "clock_type": "escalation",
                "resolution_condition": "I PG completano il colpo o gestiscono ogni indiscrezione con sufficiente discrezione",
                "discovery_hint": "I PG notano che le guardie sembrano più attente del solito — qualcosa le ha messe in allerta",
                "steps": [
                    {"value": 1, "label": "Sicurezza standard", "effect": "Routine normale — il piano originale funziona"},
                    {"value": 2, "label": "Allerta aumentata", "effect": "Turni extra notturni — la finestra dei 90 secondi è più rischiosa"},
                    {"value": 3, "label": "Sorveglianza intensificata", "effect": "Investigatori privati monitorano gli ingressi — le identità false sono a rischio"},
                    {"value": 4, "label": "Lockdown", "effect": "La banca è in lockdown — solo il piano B del tetto è ancora percorribile"}
                ],
                "ticks_per_failure": 1
            },
            {
                "id": "clock_documento_spostato",
                "label": "Spostamento del documento",
                "max_value": 3,
                "consequence": "Il direttore sposta il documento fuori dalla banca — i PG non sanno dove cercarlo",
                "clock_type": "terminal_defeat",
                "resolution_condition": "I PG trovano il documento prima che il direttore decida di spostarlo",
                "discovery_hint": "Luca riferisce che il direttore ha chiesto informazioni sulle procedure per un 'trasferimento di massima sicurezza'",
                "steps": [
                    {"value": 1, "label": "Il direttore è sospettoso", "effect": "Ordina una verifica dell'inventario della volta"},
                    {"value": 2, "label": "Il direttore pianifica il trasferimento", "effect": "Contatta un corriere di fiducia per 'spostare un oggetto delicato'"},
                    {"value": 3, "label": "Documento spostato", "effect": "Il documento è fuori dalla banca — i PG devono trovare il nuovo nascondiglio"}
                ],
                "ticks_per_failure": 1
            }
        ],
        "locations": [
            {
                "id": "loc_ingresso_banca",
                "name": "Ingresso principale della banca",
                "description": "Un atrio di marmo con due guardie sempre presenti. Le telecamere coprono ogni angolo tranne un punto cieco vicino alla scala di servizio."
            },
            {
                "id": "loc_sala_controllo",
                "name": "Sala di controllo sicurezza",
                "description": "Una stanza buia con schermi multipli che mostrano ogni telecamera della banca. Il capitano Velt lavora qui per la maggior parte del turno."
            },
            {
                "id": "loc_ufficio_direttore",
                "name": "Ufficio del Direttore",
                "description": "Un ufficio lussuoso al secondo piano. Il direttore è raramente disturbato — ma le sue carte, se trovate, raccontano una storia diversa dalla sua reputazione."
            },
            {
                "id": "loc_retro_banca",
                "name": "Area di servizio posteriore",
                "description": "L'ingresso di servizio, usato dai tecnici. Luca conosce bene questo posto — è qui che di solito aspetta i suoi contatti."
            },
            {
                "id": "loc_volta",
                "name": "Camera Forte",
                "description": "Tre porte di acciaio, ciascuna con una serratura diversa. La cassetta 447 è in fondo al terzo corridoio. Silenzio assoluto — ogni rumore risuona."
            },
            {
                "id": "loc_archivio_comunale",
                "name": "Archivio del Comune",
                "description": "Un edificio polveroso dove sono conservati i permessi di costruzione. Accesso libero durante l'orario d'ufficio — nessuno ci va mai."
            },
            {
                "id": "loc_studio_legale",
                "name": "Studio legale di Isra Morn",
                "description": "Un ufficio disordinato ma efficiente. Morn lavora sino a tardi ogni notte — basta bussare."
            }
        ]
    },

    # ── 4. Spy Mission ──────────────────────────────────────────────────────────
    {
        "id": "spy_mission",
        "title": "Operazione Doppio Specchio",
        "genre": "spy",
        "premise": (
            "I PG sono agenti di un'organizzazione di intelligence che ha scoperto che un diplomatico "
            "di alto rango sta vendendo informazioni a due fazioni nemiche contemporaneamente. "
            "La missione: infiltrarsi in un'ambasciata durante un ricevimento, identificare chi sta "
            "davvero lavorando per chi, e uscire con le prove senza scatenare un incidente internazionale."
        ),
        "hidden_truth": (
            "Il diplomatico non è un traditore ma una talpa dei PG stessi, che raccoglie informazioni "
            "facendo il doppio gioco controllato dall'organizzazione. Il vero traditore è il supervisore "
            "dei PG, che sta sabotando l'operazione per eliminare la talpa prima che riveli troppo su di lui."
        ),
        "threat_description": (
            "Il supervisore dei PG sta orchestrando la situazione perché la talpa venga eliminata "
            "durante il ricevimento — sia dai nemici che dai PG stessi. Ogni ora che passa, "
            "le possibilità che qualcuno uccida il diplomatico aumentano."
        ),
        "win_condition": (
            "Portare il diplomatico in salvo con le prove delle sue operazioni legittime, "
            "esponendo il supervisore traditore senza creare un incidente diplomatico aperto."
        ),
        "initial_hook": (
            "Il briefing del supervisore è chiaro: 'Il diplomatico Maren è un traditore. "
            "Infiltratevi al ricevimento di stasera, trovate le prove e neutralizzatelo.' "
            "Ma una nota anonima lasciata sul sedile della vostra auto dice qualcosa di diverso: "
            "'Maren lavora per voi. Siete stati mandati a uccidere il vostro uomo. Scoprite chi vi usa.'"
        ),
        "actors": [
            {
                "id": "npc_diplomatico",
                "name": "Ambasciatore Cael Maren",
                "role": "ally",
                "goal": "Completare la sua missione di raccolta informazioni senza essere eliminato dalla propria organizzazione",
                "secret": "È una talpa controllata dall'organizzazione dei PG, ma il suo supervisore vuole eliminarlo",
                "location_id": "loc_salone_ricevimento",
                "attitude": "apparentemente affabile, in realtà sempre in stato di allerta — riconosce immediatamente agenti professionisti",
                "npc_agenda": "Capire se i PG sono stati mandati ad aiutarlo o ad eliminarlo, e decidere come comportarsi",
                "pressure_response": {
                    "low": "Si comporta da diplomatico normale, ma tiene d'occhio i PG",
                    "medium": "Cerca un contatto discreto con i PG per verificare le loro intenzioni",
                    "high": "Rivela la sua vera identità se convinto che i PG siano dalla sua parte",
                    "extreme": "Si espone pubblicamente se è l'unico modo per sopravvivere"
                },
                "reaction_table": {
                    "se_minacciato": "Usa i contatti diplomatici per creare un incidente che rallenta i PG",
                    "se_i_pg_lo_aiutano": "Condivide le prove complete della sua missione legittima",
                    "se_capisce_il_tradimento_del_supervisore": "Diventa un alleato pieno e aiuta i PG a smascherarlo",
                    "se_catturato_dai_nemici": "Usa una storia di copertura preparata finché i PG non intervengono"
                },
                "current_plan": "Completare l'ultima raccolta di informazioni al ricevimento poi sparire",
                "fallback_plan": "Rivelare pubblicamente tutto se la propria vita è in pericolo immediato"
            },
            {
                "id": "npc_supervisore",
                "name": "Supervisore Dren Cass",
                "role": "villain",
                "goal": "Far eliminare Maren prima che riveli il suo doppio gioco, usando i PG come strumento inconsapevole",
                "secret": "Sta vendendo informazioni a una terza fazione — Maren lo sa ed è un pericolo per lui",
                "location_id": "loc_quartier_generale",
                "attitude": "professionale, paterno, apparentemente dalla parte dei PG — è la loro fonte principale",
                "npc_agenda": "Guidare i PG a eliminare Maren, poi screditare qualsiasi accusa post-missione",
                "agenda_pressure": 10,
                "pressure_response": {
                    "low": "Gestisce i PG a distanza con briefing regolari e falso supporto",
                    "medium": "Inizia a mettere in dubbio la sanità mentale o la lealtà dei PG se deviamo",
                    "high": "Manda agenti nemici a eliminare i PG quando capisce che stanno scoprendo la verità",
                    "extreme": "Fugge con tutti i file compromettenti verso un paese senza estradizione"
                },
                "reaction_table": {
                    "se_i_pg_sospettano": "Produce false prove della lealtà e si mostra ferito dal dubbio",
                    "se_smascherato": "Mette in atto un piano di uscita preparato in anticipo",
                    "se_i_pg_hanno_prove": "Cerca di distruggerle o screditare le fonti",
                    "se_catturato": "Nega tutto e chiede un avvocato — ha coperture legali robuste"
                },
                "current_plan": "Monitorare i PG e assicurarsi che completino la missione originale",
                "fallback_plan": "Attivare l'agente dormiente all'ambasciata per eliminare sia Maren che i PG"
            },
            {
                "id": "npc_agente_nemico",
                "name": "Agente Sola Vik",
                "role": "antagonist",
                "goal": "Ottenere le prove delle attività di Maren per la sua organizzazione e neutralizzarlo",
                "secret": "Sa che il supervisore dei PG è un doppio agente — potrebbe diventare un'alleata inaspettata",
                "location_id": "loc_salone_ricevimento",
                "attitude": "fredda, professionale, apparentemente una diplomatica dell'ambasciata",
                "npc_agenda": "Completare la sua missione ma non a spese di una potenziale relazione futura con i PG",
                "agenda_pressure": 7,
                "pressure_response": {
                    "low": "Osserva i PG valutando se sono alleati o ostacoli",
                    "medium": "Cerca di distoglierli da Maren con false informazioni",
                    "high": "Impegna i PG in un confronto diretto se blocca la sua missione",
                    "extreme": "Propone un'alleanza temporanea contro il supervisore se capisce la situazione reale"
                },
                "reaction_table": {
                    "se_i_pg_la_scoprono": "Propone una tregua e condivide le sue informazioni sul supervisore",
                    "se_minacciata": "Usa tecniche di combattimento professionali — non è una civile",
                    "se_coopera": "Fornisce prove del doppio gioco del supervisore che la sua organizzazione ha raccolto",
                    "se_maren_e_in_pericolo": "Valuta se è più utile salvarlo o lasciarlo andare"
                },
                "current_plan": "Avvicinarsi a Maren durante il ricevimento e proporre un accordo",
                "fallback_plan": "Estrarre le informazioni con la forza se necessario e scomparire"
            },
            {
                "id": "npc_contatto_locale",
                "name": "Amira il Contatto",
                "role": "ally",
                "goal": "Aiutare i PG a muoversi nell'ambasciata in cambio di protezione per la sua famiglia",
                "secret": "Lavora nell'ambasciata come personale e conosce ogni stanza e ogni routine",
                "location_id": "loc_salone_ricevimento",
                "attitude": "spaventata ma decisa — non ha altra scelta",
                "npc_agenda": "Fornire ai PG l'accesso e le informazioni necessarie, poi sparire in sicurezza",
                "pressure_response": {
                    "low": "Guida i PG con indicazioni discrete",
                    "medium": "Li aiuta ad accedere alle aree riservate",
                    "high": "Si espone personalmente per coprire i PG in una situazione critica",
                    "extreme": "Rivela informazioni vitali anche a costo della propria copertura"
                },
                "reaction_table": {
                    "se_minacciata": "Chiede protezione immediata e smette di collaborare finché non è al sicuro",
                    "se_i_pg_la_proteggono": "Fornisce accesso completo e ogni informazione che ha",
                    "se_scoperta": "Si costruisce una storia di copertura, ma ha bisogno di supporto",
                    "se_la_famiglia_e_al_sicuro": "Diventa un'alleata pienamente impegnata"
                },
                "current_plan": "Aiutare i PG a navigare il ricevimento senza esporsi",
                "fallback_plan": "Consegnare le informazioni e sparire in un rifugio preparato"
            },
            {
                "id": "npc_agente_dormiente",
                "name": "Agente Dormiente (Identità ignota)",
                "role": "antagonist",
                "goal": "Ricevere l'ordine del supervisore ed eliminare i PG e Maren al momento opportuno",
                "secret": "È un membro del personale di sicurezza dell'ambasciata — la sua vera identità è sconosciuta fino al momento dell'azione",
                "location_id": "loc_sala_sicurezza",
                "attitude": "professionale, invisibile, integrato nel personale dell'ambasciata",
                "npc_agenda": "Attendere l'ordine e colpire al momento ottimale",
                "agenda_pressure": 8,
                "pressure_response": {
                    "low": "Svolge il normale lavoro di sicurezza, non fa nulla che attiri l'attenzione",
                    "medium": "Inizia a posizionarsi strategicamente vicino ai PG e a Maren",
                    "high": "Attacca quando ha l'opportunità — cerca di far sembrare un incidente",
                    "extreme": "Se scoperto, tenta un'uscita di sicurezza e attiva protocolli di emergenza"
                },
                "reaction_table": {
                    "se_scoperto_prima_dellazione": "Nega tutto e si eclissa — il supervisore lo proteggerà",
                    "se_i_pg_hanno_la_sua_identita": "Colpisce immediatamente senza aspettare l'ordine",
                    "se_il_supervisore_viene_smascherato": "L'ordine non arriva mai — rimane nella sua copertura",
                    "se_catturato": "Rivela il supervisore in cambio di trattamento migliore"
                },
                "current_plan": "Attendere l'ordine del supervisore e agire nel momento di massimo caos",
                "fallback_plan": "Se l'ordine non arriva, scomparire prima che la missione finisca"
            }
        ],
        "clues": [
            {
                "id": "clue_nota_anonima",
                "label": "Nota anonima",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_quartier_generale",
                "reveals": "Qualcuno ha avvertito i PG che la loro missione è una trappola",
                "immediate_information": "La nota sul sedile dell'auto: 'Maren lavora per voi. Siete stati mandati a uccidere il vostro uomo. Scoprite chi vi usa.'",
                "hidden_implication": "Il mittente della nota è probabilmente Maren stesso o qualcuno che lavora con lui — sa che i PG sono stati ingannati",
                "possible_actions": ["Indagare sull'autore della nota", "Avvicinarsi a Maren con cautela invece di neutralizzarlo", "Informarsi sull'organizzazione dal di dentro"]
            },
            {
                "id": "clue_dossier_maren",
                "label": "Dossier reale di Maren",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_archivio_segreto",
                "reveals": "Il vero dossier di Maren mostra che è una talpa autorizzata, non un traditore",
                "immediate_information": "Nell'archivio segreto dell'organizzazione, un fascicolo con il timbro 'Operazione Autorizzata' mostra che Maren sta raccogliendo informazioni su ordine dell'organizzazione stessa",
                "hidden_implication": "Il supervisore ha nascosto questo dossier e ha fornito ai PG solo le informazioni che lo facevano sembrare un traditore",
                "possible_actions": ["Confrontare il dossier con il briefing del supervisore", "Usarlo per convincere Maren che i PG non sono nemici", "Portarlo come prova del sabotaggio del supervisore"]
            },
            {
                "id": "clue_transazioni_supervisore",
                "label": "Bonifici del supervisore",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_archivio_segreto",
                "reveals": "Il supervisore sta ricevendo pagamenti da una terza fazione nemica",
                "immediate_information": "Estratti conto off-shore collegati al supervisore, trovati nell'archivio, mostrano trasferimenti regolari da un'entità straniera",
                "hidden_implication": "Il supervisore ha interesse diretto a eliminare Maren perché Maren conosce i dettagli del suo tradimento",
                "possible_actions": ["Usare i bonifici come prova contro il supervisore", "Mostrare i bonifici a un superiore del supervisore", "Ricattare il supervisore per fermare l'operazione"]
            },
            {
                "id": "clue_agente_dormiente_identita",
                "label": "Lista del personale di sicurezza",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_sala_sicurezza",
                "reveals": "Uno dei membri del personale di sicurezza ha un passato militare incompatibile con il suo profilo dichiarato",
                "immediate_information": "La lista del personale dell'ambasciata mostra un agente con credenziali troppo recenti e un background che non regge a un'analisi attenta",
                "hidden_implication": "È l'agente dormiente del supervisore — se i PG lo identificano prima, possono neutralizzare la minaccia",
                "possible_actions": ["Tenere d'occhio l'agente dormiente", "Informare Amira per isolare la minaccia", "Neutralizzarlo prima che riceva l'ordine"]
            },
            {
                "id": "clue_conversazione_vik",
                "label": "Conversazione intercettata",
                "type": "testimony",
                "thread_id": "T2",
                "source_location": "loc_salone_ricevimento",
                "reveals": "Sola Vik menziona in una conversazione che 'il supervisore dei PG ha fatto una mossa stupida'",
                "immediate_information": "Intercettando una chiamata di Vik, i PG sentono: 'Il Cass ha venduto fuori il suo agente per coprirsi. Adesso sa che lo sappiamo.'",
                "hidden_implication": "Anche la fazione nemica sa che il supervisore è corrotto — potrebbe diventare un'alleata se i PG si avvicinano nel modo giusto",
                "possible_actions": ["Avvicinarsi a Vik e proporre una collaborazione", "Usare questa informazione per smascherare il supervisore", "Condividere l'intercettazione con il comando dell'organizzazione"]
            }
        ],
        "story_threads": [
            {
                "id": "T1",
                "title": "Proteggere Maren dall'agente dormiente",
                "question": "Chi è l'agente dormiente e come neutralizzarlo prima che agisca?",
                "true_answer": "L'agente dormiente è infiltrato nel personale di sicurezza — il suo profilo nella lista rivela l'incongruenza",
                "required_clues": ["clue_agente_dormiente_identita"],
                "minimum_clues_to_deduce": 1,
                "payoff": "Neutralizzare la minaccia immediata su Maren e creare spazio per far emergere la verità"
            },
            {
                "id": "T2",
                "title": "Chi è il vero traditore?",
                "question": "È davvero Maren il traditore, o i PG sono stati usati per eliminarlo?",
                "true_answer": "Il supervisore Cass è il vero traditore — ha usato i PG per eliminare Maren che sapeva troppo",
                "required_clues": ["clue_nota_anonima", "clue_dossier_maren", "clue_transazioni_supervisore"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Capire la vera struttura del tradimento, proteggere Maren e smascherare il supervisore"
            }
        ],
        "event_clocks": [
            {
                "id": "clock_ordine_agente_dormiente",
                "label": "Ordine all'agente dormiente",
                "max_value": 4,
                "consequence": "Il supervisore attiva l'agente dormiente — attacco simultaneo a Maren e ai PG nel caos del ricevimento",
                "clock_type": "terminal_defeat",
                "resolution_condition": "I PG neutralizzano l'agente dormiente o smascherano il supervisore prima che dia l'ordine",
                "discovery_hint": "Amira nota che uno del personale ha il telefono in mano tutto il tempo — sta aspettando una chiamata",
                "steps": [
                    {"value": 1, "label": "Il supervisore monitora la situazione", "effect": "Il supervisore chiede aggiornamenti ogni 30 minuti — è nervoso"},
                    {"value": 2, "label": "Il supervisore perde pazienza", "effect": "Manda un messaggio all'agente dormiente: 'prepararsi'"},
                    {"value": 3, "label": "Finalizzazione ordine", "effect": "L'agente dormiente si posiziona — i PG hanno pochi minuti per agire"},
                    {"value": 4, "label": "L'ordine è dato", "effect": "L'agente dormiente attacca — combattimento nel bel mezzo del ricevimento diplomatico"}
                ],
                "ticks_per_failure": 1
            },
            {
                "id": "clock_copertura_maren",
                "label": "Copertura di Maren compromessa",
                "max_value": 3,
                "consequence": "L'identità di Maren come talpa viene rivelata alla fazione nemica — è in pericolo immediato",
                "clock_type": "escalation",
                "resolution_condition": "I PG proteggono Maren o lo estraggono dal ricevimento prima che la sua identità venga scoperta",
                "discovery_hint": "Vik sembra improvvisamente molto interessata a Maren — lo osserva con un'attenzione che non ha niente di sociale",
                "steps": [
                    {"value": 1, "label": "Vik sospetta di Maren", "effect": "L'agente nemica inizia a fare domande discrete sull'ambasciatore"},
                    {"value": 2, "label": "Vik ha conferme", "effect": "La fazione nemica sa che Maren è una talpa — lo mettono sotto sorveglianza"},
                    {"value": 3, "label": "Maren identificato", "effect": "La fazione nemica tenta di estrarre Maren con la forza"}
                ],
                "ticks_per_failure": 1
            }
        ],
        "locations": [
            {
                "id": "loc_salone_ricevimento",
                "name": "Salone del Ricevimento",
                "description": "Un salone dorato con centinaia di diplomatici, giornalisti e personale. La musica copre le conversazioni discrete. Ogni angolo nasconde un occhio che guarda."
            },
            {
                "id": "loc_archivio_segreto",
                "name": "Archivio Riservato dell'Organizzazione",
                "description": "Una stanza sicura accessibile solo con le credenziali giuste. I veri dossier delle operazioni sono qui — inclusi quelli che il supervisore voleva tenere nascosti."
            },
            {
                "id": "loc_sala_sicurezza",
                "name": "Sala di Sicurezza dell'Ambasciata",
                "description": "Il centro operativo del personale di sicurezza dell'ambasciata. Liste del personale, rotazione turni, protocolli di emergenza — tutto è qui."
            },
            {
                "id": "loc_quartier_generale",
                "name": "Quartier Generale dell'Organizzazione",
                "description": "L'ufficio del supervisore e la sala briefing. Sembra un ambiente sicuro — ma il pericolo qui è il più vicino."
            },
            {
                "id": "loc_uscita_sicurezza",
                "name": "Uscita di Sicurezza",
                "description": "Un corridoio di servizio che porta al parcheggio interno. Poco sorvegliato, è il punto di estrazione ideale per portare Maren in salvo."
            }
        ]
    },

    # ── 5. Horror Mansion ───────────────────────────────────────────────────────
    {
        "id": "horror_mansion",
        "title": "Villa Morente",
        "genre": "horror",
        "premise": (
            "I personaggi sono bloccati in una villa vittoriana isolata durante una tempesta notturna. "
            "Il padrone di casa è stato trovato morto al piano di sopra con un'espressione di terrore assoluto. "
            "Le porte non si aprono, il telefono è muto, e da qualche parte nelle stanze buie "
            "qualcosa si muove con una logica che sfugge alla comprensione."
        ),
        "hidden_truth": (
            "Il padrone di casa praticava riti di evocazione nel seminterrato. Tre settimane fa "
            "ha commesso un errore — qualcosa è entrato nella villa e non vuole uscire. "
            "Non uccide a caso: vuole essere liberato dal rituale che lo ha intrappolato qui, "
            "ma non sa come comunicarlo se non attraverso il terrore."
        ),
        "threat_description": (
            "La presenza nella villa diventa più instabile man mano che la notte avanza. "
            "La sanità collettiva dei personaggi si erode con ogni scoperta. "
            "All'alba, chi non ha trovato il rituale di liberazione sarà perduto."
        ),
        "win_condition": (
            "Trovare ed eseguire il rituale di liberazione dal manuale del padrone di casa "
            "prima dell'alba, oppure trovare un modo per distruggere fisicamente il focus "
            "del rituale originale nel seminterrato."
        ),
        "initial_hook": (
            "La tempesta vi ha obbligato a fermarvi. Il padrone di casa — un vecchio professore "
            "dall'aria eccentrica — vi ha accolti con entusiasmo. Poi, a mezzanotte, un urlo "
            "dal piano di sopra. Lo avete trovato sul pavimento del suo studio, morto, "
            "gli occhi spalancati verso qualcosa che non esiste. E le porte della villa "
            "non si aprono dall'interno."
        ),
        "actors": [
            {
                "id": "npc_presenza",
                "name": "La Presenza (Entità senza nome)",
                "role": "antagonist",
                "goal": "Essere liberata dal rituale che la tiene vincolata alla villa",
                "secret": "Non vuole fare del male — sta cercando disperatamente di comunicare, ma la sua natura causa terrore involontario",
                "location_id": "loc_seminterrato",
                "attitude": "spaventosa ma non malvagia — ogni manifestazione è un tentativo di comunicazione distorto",
                "npc_agenda": "Guidare i PG verso il rituale di liberazione, anche se i suoi tentativi di comunicazione li terrorizzano",
                "agenda_pressure": 6,
                "pressure_response": {
                    "low": "Manifestazioni ambientali leggere: luci che tremolano, voci lontane",
                    "medium": "Immagini e visioni che mostrano frammenti del rituale originale",
                    "high": "Apparizioni dirette che spingono i PG verso il seminterrato",
                    "extreme": "Perde il controllo — le manifestazioni diventano fisicamente pericolose"
                },
                "reaction_table": {
                    "se_i_pg_si_avvicinano_al_seminterrato": "Le manifestazioni si calmano — è sulla strada giusta",
                    "se_i_pg_fuggono": "Le manifestazioni si intensificano — l'entità è frustrata",
                    "se_i_pg_trovano_il_manuale": "Una calma innaturale pervade la stanza dove si trovano",
                    "se_il_rituale_viene_eseguito": "Si libera — l'alba arriva, le porte si aprono"
                },
                "current_plan": "Guidare i PG verso le prove del rituale di liberazione",
                "fallback_plan": "Se i PG non capiscono, tentare manifestazioni sempre più dirette anche a costo di spaventarli"
            },
            {
                "id": "npc_domestica",
                "name": "Elsa la Domestica",
                "role": "neutral",
                "goal": "Sopravvivere alla notte proteggendo se stessa e — se possibile — gli ospiti",
                "secret": "Sa che il professore conduceva esperimenti nel seminterrato e ha visto la sua sanità deteriorarsi nelle ultime settimane",
                "location_id": "loc_cucina",
                "attitude": "terrorizzata ma pragmatica — conosce la villa meglio di chiunque altro",
                "npc_agenda": "Restare al sicuro in cucina, ma aiutare i PG se capisce che è l'unica via per sopravvivere",
                "pressure_response": {
                    "low": "Si chiude in cucina e rifiuta di parlare",
                    "medium": "Risponde alle domande dei PG con risposte parziali",
                    "high": "Accompagna i PG nelle aree meno pericolose e condivide tutto quello che sa",
                    "extreme": "Si sacrifica per permettere ai PG di raggiungere il seminterrato"
                },
                "reaction_table": {
                    "se_minacciata_dalla_presenza": "Crolla e rivela tutto quello che sa sul professore",
                    "se_i_pg_la_proteggono": "Diventa un'alleata piena e guida i PG attraverso la villa",
                    "se_tradita": "Si rinchiude in cucina e non apre più per nessun motivo",
                    "se_i_pg_trovano_il_manuale": "Li aiuta a interpretare le istruzioni del rituale"
                },
                "current_plan": "Aspettare in cucina che qualcuno trovi una soluzione",
                "fallback_plan": "Se la presenza si intensifica, rompe una finestra e fugge nella tempesta"
            },
            {
                "id": "npc_ospite_scettico",
                "name": "Dottor Hannes Roth",
                "role": "neutral",
                "goal": "Trovare una spiegazione razionale per tutto e organizzare un'uscita di sicurezza",
                "secret": "In gioventù ha avuto un'esperienza soprannaturale che non ammette mai — sa che queste cose esistono",
                "location_id": "loc_salotto",
                "attitude": "razionale, autoritario, scettico dichiarato che nasconde una paura profonda",
                "npc_agenda": "Convincere tutti che c'è una spiegazione normale e organizzare la fuga dall'edificio",
                "pressure_response": {
                    "low": "Cerca spiegazioni razionali e organizza ricognizioni metodiche",
                    "medium": "Inizia ad ammettere che qualcosa non va, ma cerca ancora soluzioni pragmatiche",
                    "high": "La facciata scettica crolla — aiuta i PG con le sue conoscenze sommerse",
                    "extreme": "Rivela la sua esperienza passata e diventa l'esperto inaspettato del gruppo"
                },
                "reaction_table": {
                    "se_le_manifestazioni_sono_evidenti": "Cerca ancora di razionalizzare, ma inizia a cedere",
                    "se_i_pg_hanno_il_manuale": "Lo esamina con competenza inaspettata",
                    "se_la_sua_sanita_scende": "Perde temporaneamente lucidità e deve essere supportato",
                    "se_il_rituale_funziona": "Ammette in silenzio quello che ha sempre saputo"
                },
                "current_plan": "Trovare un modo fisico per aprire le porte e uscire",
                "fallback_plan": "Se le porte restano chiuse, accettare la realtà soprannaturale e cooperare"
            },
            {
                "id": "npc_ospite_sensitivo",
                "name": "Mei l'Artista",
                "role": "ally",
                "goal": "Capire cosa vuole la presenza e trovare un modo per comunicare con lei",
                "secret": "Ha una sensibilità soprannaturale latente che non ha mai esplorato — la presenza la riconosce",
                "location_id": "loc_salotto",
                "attitude": "aperta, creativa, spaventata ma affascinata",
                "npc_agenda": "Usare la sua sensibilità per interpretare i messaggi della presenza e guidare il gruppo",
                "pressure_response": {
                    "low": "Percepisce le manifestazioni prima degli altri — avverte il gruppo",
                    "medium": "Riceve immagini e intuizioni che indicano la via verso il rituale",
                    "high": "Diventa un canale temporaneo per la presenza — le sue parole guidano il gruppo",
                    "extreme": "La connessione con la presenza la mette in pericolo — ha bisogno di protezione fisica mentre guida"
                },
                "reaction_table": {
                    "se_il_gruppo_la_sostiene": "Le sue intuizioni diventano sempre più precise e utili",
                    "se_lasciata_sola": "La connessione con la presenza la sopraffà temporaneamente",
                    "se_la_sua_sanita_scende": "Le visioni diventano confuse e contraddittorie",
                    "se_il_rituale_e_eseguito": "Percepisce la liberazione e piange di sollievo"
                },
                "current_plan": "Seguire le sensazioni e cercare di capire cosa vuole la villa",
                "fallback_plan": "Se le visioni diventano troppo intense, chiedere al gruppo di fermarla fisicamente"
            }
        ],
        "clues": [
            {
                "id": "clue_diario_professore",
                "label": "Diario del professore",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_studio",
                "reveals": "Il professore descrive il rituale che ha condotto tre settimane fa e l'errore che ha commesso",
                "immediate_information": "Un diario rilegato nello studio del professore. Le ultime pagine descrivono un 'rituale di apertura' e 'qualcosa che è entrato quando non avrebbe dovuto'",
                "hidden_implication": "Il professore sapeva che la presenza era intrappolata — stava cercando il rituale di liberazione quando è morto",
                "possible_actions": ["Trovare il manuale del rituale citato nel diario", "Capire cosa è andato storto tre settimane fa", "Cercare indizi sulla localizzazione del focus nel seminterrato"]
            },
            {
                "id": "clue_manuale_rituale",
                "label": "Manuale del rituale di liberazione",
                "type": "document",
                "thread_id": "T2",
                "source_location": "loc_biblioteca",
                "reveals": "Il rituale esatto per liberare la presenza dalla villa, con i componenti necessari",
                "immediate_information": "Un vecchio volume in latino nella biblioteca, con segnalibri recenti del professore. Contiene il 'Rito di Scioglimento' — tre componenti fisici, una formula, e deve essere eseguito al centro del focus",
                "hidden_implication": "Il professore aveva trovato il manuale — è morto prima di poterlo usare. I componenti del rituale sono già nella villa",
                "possible_actions": ["Identificare i tre componenti necessari", "Trovare il focus nel seminterrato", "Eseguire il rituale con Mei come guida spirituale"]
            },
            {
                "id": "clue_manifestazione_visiva",
                "label": "Visione nel corridoio",
                "type": "location_detail",
                "thread_id": "T1",
                "source_location": "loc_corridoio_primo_piano",
                "reveals": "La presenza proietta immagini del seminterrato — sta cercando di guidare i PG verso il focus",
                "immediate_information": "Nel corridoio buio, una figura fosforescente appare brevemente e sembra indicare verso la scala del seminterrato prima di dissolversi",
                "hidden_implication": "La presenza non sta attaccando — sta mostrando la via. Le sue manifestazioni sono tentativi di comunicazione, non di aggressione",
                "possible_actions": ["Seguire la direzione indicata", "Registrare le visioni per trovare un pattern", "Condividere l'osservazione con Mei per interpretarla"]
            },
            {
                "id": "clue_focus_rituale",
                "label": "Sigillo inciso nel seminterrato",
                "type": "physical_evidence",
                "thread_id": "T2",
                "source_location": "loc_seminterrato",
                "reveals": "Il punto fisico dove il rituale originale è stato condotto — il centro del collegamento con la presenza",
                "immediate_information": "Sul pavimento del seminterrato, un elaborato sigillo geometrico inciso nella pietra, con candele consumate e resti di componenti rituali",
                "hidden_implication": "Questo è il focus — il rituale di liberazione deve essere eseguito qui, sopra questo stesso sigillo",
                "possible_actions": ["Identificare il centro esatto del sigillo", "Controllare se i componenti originali sono ancora usabili", "Preparare il sito per il rituale di liberazione"]
            },
            {
                "id": "clue_sanita_tracce",
                "label": "Note psichiatriche del professore",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_studio",
                "reveals": "La presenza causa deterioramento mentale progressivo — il professore lo aveva documentato su se stesso",
                "immediate_information": "Fogli scritti a mano con grafia sempre più irregolare: il professore descriveva visioni, paranoie, poi 'la certezza che la cosa non vuole male'",
                "hidden_implication": "La sanità si erode — ma chi la perde interamente potrebbe vedere cose che gli altri non possono. Un PG che sacrifica parte della propria sanità potrebbe vedere il rituale completo",
                "possible_actions": ["Usare la perdita di sanità come strumento per ricevere visioni complete", "Trovare un modo per rallentare il deterioramento", "Identificare chi è più resistente e chi più aperto"]
            },
            {
                "id": "clue_componenti_rituale",
                "label": "Componenti del rituale sparsi nella villa",
                "type": "physical_evidence",
                "thread_id": "T2",
                "source_location": "loc_cucina",
                "reveals": "I tre componenti necessari per il rituale di liberazione sono nascosti in diverse stanze",
                "immediate_information": "Elsa ricorda che il professore le aveva chiesto di tenere 'quelle tre cose speciali' in posti separati — un cristallo in cucina, un libro antico in biblioteca, una chiave di rame nello studio",
                "hidden_implication": "Il professore aveva già preparato i componenti del rituale — stava per eseguirlo quando è morto. Tutto è pronto, mancano solo i PG",
                "possible_actions": ["Raccogliere il cristallo dalla cucina", "Prendere il libro dalla biblioteca (potrebbe già essere il manuale)", "Trovare la chiave di rame nello studio del professore"]
            },
            {
                "id": "clue_aringa_rossa",
                "label": "Libro proibito sull'evocazione",
                "type": "document",
                "thread_id": "T1",
                "source_location": "loc_biblioteca",
                "reveals": "Un libro che sembra contenere il rituale di evocazione — ma è una falsa pista",
                "immediate_information": "Un volume dall'aspetto sinistro con simboli rossi. Sembra il manuale originale dell'evocazione — il tono suggerisce una presenza malvagia da distruggere",
                "hidden_implication": "Questo libro descrive come evocare la presenza, non come liberarla. Seguire le sue istruzioni la intrappolerebbero ancora più a fondo — o peggio",
                "possible_actions": ["Leggerlo con attenzione prima di seguirne le istruzioni", "Confrontarlo con il diario del professore per capire le differenze", "Ignorarlo come fonte inaffidabile se si ha già il manuale corretto"]
            }
        ],
        "story_threads": [
            {
                "id": "T1",
                "title": "Cosa è successo al professore e cosa vuole la presenza",
                "question": "Chi o cosa ha ucciso il professore, e la presenza è una minaccia o qualcos'altro?",
                "true_answer": "La presenza non voleva uccidere il professore — il professore è morto di paura durante una manifestazione intensa. La presenza vuole essere liberata, non fare del male",
                "required_clues": ["clue_diario_professore", "clue_manifestazione_visiva", "clue_sanita_tracce"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Capire che la presenza non è un nemico ma un essere intrappolato che chiede aiuto — cambia completamente l'approccio del gruppo"
            },
            {
                "id": "T2",
                "title": "Come liberare la presenza e sopravvivere all'alba",
                "question": "Come si esegue il rituale di liberazione e dove si trova il focus?",
                "true_answer": "Il rituale richiede tre componenti fisici (cristallo, libro, chiave), la formula nel manuale, e deve essere eseguito sul sigillo nel seminterrato prima dell'alba",
                "required_clues": ["clue_manuale_rituale", "clue_focus_rituale", "clue_componenti_rituale"],
                "minimum_clues_to_deduce": 2,
                "payoff": "Eseguire con successo il rituale di liberazione, permettendo alla presenza di andare via e alle porte di aprirsi all'alba"
            }
        ],
        "event_clocks": [
            {
                "id": "clock_sanita_collettiva",
                "label": "Sanità collettiva del gruppo",
                "max_value": 5,
                "consequence": "Il gruppo perde la capacità di agire razionalmente — le visioni diventano indistinguibili dalla realtà e il rituale non può essere eseguito correttamente",
                "clock_type": "escalation",
                "resolution_condition": "Trovare il manuale del rituale e iniziare la preparazione stabilizza temporaneamente la sanità del gruppo",
                "discovery_hint": "Tutti iniziano a vedere le stesse ombre negli angoli — ma le vedono in posti diversi",
                "steps": [
                    {"value": 1, "label": "Disagio crescente", "effect": "Tutti i personaggi subiscono -1 a tiri basati sulla concentrazione — la villa pesa"},
                    {"value": 2, "label": "Visioni sporadiche", "effect": "I PG vedono cose che non ci sono — difficile distinguere indizi reali da allucinazioni"},
                    {"value": 3, "label": "Paranoia intergruppo", "effect": "I PG tendono a sospettarsi a vicenda — cooperare diventa difficile"},
                    {"value": 4, "label": "Sanità fragile", "effect": "Qualsiasi stimolo forte può causare una reazione incontrollata — il pericolo viene da dentro oltre che da fuori"},
                    {"value": 5, "label": "Collasso mentale", "effect": "Il gruppo non riesce più a eseguire il rituale con lucidità — serve un ultimo sforzo eroico"}
                ],
                "ticks_per_failure": 1
            },
            {
                "id": "clock_alba",
                "label": "L'Alba si avvicina",
                "max_value": 6,
                "consequence": "L'alba arriva senza rituale — la presenza perde completamente il controllo. Le porte si aprono, ma la presenza si manifesta nel mondo esterno",
                "clock_type": "terminal_defeat",
                "resolution_condition": "Eseguire il rituale di liberazione prima che l'orologio raggiunga il massimo",
                "discovery_hint": "L'orologio della villa suona le ore — ogni ora porta l'alba più vicina e la presenza più instabile",
                "steps": [
                    {"value": 1, "label": "Mezzanotte", "effect": "La villa è bloccata. Il professore è morto. La notte comincia."},
                    {"value": 2, "label": "L'una di notte", "effect": "Le manifestazioni si intensificano — la presenza è inquieta"},
                    {"value": 3, "label": "Le due di notte", "effect": "Metà notte. Senza rituale, la presenza sta perdendo la stabilità"},
                    {"value": 4, "label": "Le tre di notte", "effect": "Ora delle tenebre — le manifestazioni sono al picco. Il seminterrato è pericoloso ma necessario"},
                    {"value": 5, "label": "Le quattro di notte", "effect": "L'alba si avvicina. La presenza lo sente e diventa disperata"},
                    {"value": 6, "label": "L'alba", "effect": "Senza rituale, la presenza si manifesta pienamente. Il gruppo deve combattere o fuggire"}
                ],
                "ticks_per_failure": 1
            }
        ],
        "locations": [
            {
                "id": "loc_salotto",
                "name": "Salotto principale",
                "description": "Un salotto buio con mobili victroriani, un camino spento e ritratti di famiglia che sembrano guardare. La porta verso l'esterno è bloccata."
            },
            {
                "id": "loc_studio",
                "name": "Studio del professore",
                "description": "Scaffali pieni di libri esotici, una scrivania coperta di note, e il corpo del professore sul pavimento. I suoi occhi guardano ancora verso qualcosa che non c'è."
            },
            {
                "id": "loc_biblioteca",
                "name": "Biblioteca",
                "description": "Migliaia di volumi in lingue diverse. Alcuni scaffali sono stati svuotati di recente — il professore cercava qualcosa di specifico fino a poco prima."
            },
            {
                "id": "loc_cucina",
                "name": "Cucina",
                "description": "L'unica stanza con una luce ancora accesa. Elsa si è barricata qui. Odore di pane e qualcosa di bruciato — una candela consumata sul tavolo."
            },
            {
                "id": "loc_corridoio_primo_piano",
                "name": "Corridoio del primo piano",
                "description": "Un lungo corridoio buio dove le manifestazioni della presenza sono più intense. Luci che tremolano, porte che si aprono e si chiudono, figure che scompaiono."
            },
            {
                "id": "loc_seminterrato",
                "name": "Seminterrato rituale",
                "description": "Buio totale, odore di zolfo e cera. Sul pavimento di pietra, il sigillo inciso brilla debolmente. Questo è il cuore del problema — e la soluzione."
            }
        ]
    },
]

# ── Index ───────────────────────────────────────────────────────────────────────

def get_template_list() -> list:
    """Returns a summary list of available templates for the GET /adventure/templates endpoint."""
    result = []
    for t in ADVENTURE_TEMPLATES:
        result.append({
            "id": t["id"],
            "title": t["title"],
            "genre": t["genre"],
            "description": t.get("premise", "")[:200],
            "npc_count": len(t.get("actors", [])),
            "clue_count": len(t.get("clues", [])),
            "clock_count": len(t.get("event_clocks", [])),
        })
    return result


def get_template_by_id(template_id: str) -> dict | None:
    """Returns the full template dict for the given id, or None if not found."""
    for t in ADVENTURE_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
