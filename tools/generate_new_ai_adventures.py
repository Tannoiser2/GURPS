#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "compiled_adventures"


def actor(slug, name, role, loc, desc, goal, secret, plan, fallback, pressure=5):
    return {
        "id": f"actor_{slug}",
        "name": name,
        "role": role,
        "location_id": loc,
        "description": desc,
        "goal": goal,
        "motivation": goal,
        "secret": secret,
        "attitude": "hostile" if role == "antagonist" else ("friendly" if role == "ally" else "suspicious"),
        "agenda_pressure": pressure,
        "current_plan": plan,
        "fallback_plan": fallback,
        "pressure_response": {
            "low": f"{name} osserva e testa i PG senza esporsi, lasciando trapelare solo informazioni controllate.",
            "medium": f"{name} accelera il proprio piano e usa contatti, minacce o favori per spostare la scena a suo vantaggio.",
            "high": f"{name} sacrifica risorse secondarie, elimina prove fragili e forza i PG a scegliere tra sicurezza e verita.",
            "extreme": f"{name} tenta la mossa finale: fuga, tradimento aperto o attivazione del pericolo principale.",
        },
        "reaction_table": {
            "se_minacciato": "Si chiude, concede una mezza verita utile ma cerca una via di fuga o un testimone.",
            "se_corrotto_o_pagato": "Accetta solo se il pagamento risolve un bisogno immediato; chiede garanzie concrete.",
            "se_i_pg_hanno_prove": "Cambia tono, prova a reinterpretare le prove e rivela un tassello verificabile.",
            "se_alleato": "Condivide una risorsa pratica e avverte dei rischi che non può affrontare da solo.",
        },
    }


def loc(slug, name, desc, exits, start=False, hazards=None):
    return {
        "id": f"loc_{slug}",
        "name": name,
        "description": desc,
        "exits": [f"loc_{e}" for e in exits],
        "is_starting_location": start,
        "type": "site",
        "access_state": "open",
        "visual_identity": desc,
        "gameplay_function": "Indagare, negoziare, muoversi verso il prossimo nodo e scoprire indizi.",
        "hazards": hazards or [],
        "clue_slots": [],
    }


def clue(slug, label, kind, thread, source, reveals, payoff, hidden, wrong):
    return {
        "id": f"clue_{slug}",
        "label": label,
        "type": kind,
        "thread_id": thread,
        "source_location": source,
        "reveals": reveals,
        "payoff": payoff,
        "state": "hidden",
        "progress_ticks": 0,
        "is_required": True,
        "revelation_ids": [f"rev_{thread}", "rev_solution"],
        "immediate_information": reveals,
        "hidden_implication": hidden,
        "unlocks": [],
        "possible_actions": ["Esaminare la scena", "Interrogare un NPC collegato", "Incrociare con un altro indizio"],
        "wrong_interpretations": wrong,
        "source_status": "generated",
        "confidence": 0.9,
    }


def clock(slug, label, consequence, resolution, clue_id):
    return {
        "id": f"clock_{slug}",
        "label": label,
        "value": 0,
        "max_value": 10,
        "consequence": consequence,
        "active": True,
        "on_complete": "terminal_defeat",
        "steps": [
            {"tick": 2, "event": "Primi segnali visibili: allarmi, voci, presagi o movimenti nemici."},
            {"tick": 4, "event": "Una risorsa sicura diventa instabile e un NPC cambia posizione."},
            {"tick": 6, "event": "Il pericolo colpisce un innocente o distrugge una prova secondaria."},
            {"tick": 8, "event": "Il fronte avversario forza una scelta immediata con costi concreti."},
            {"tick": 10, "event": consequence},
        ],
        "clock_type": "terminal_defeat",
        "resolution_clues": [clue_id],
        "resolution_condition": resolution,
        "resolved": False,
        "auto_balance": True,
        "discovered": False,
        "discovery_clue_id": clue_id,
        "discovery_hint": "I segnali del clock sono percepibili prima che diventi irreversibile.",
        "ticks_per_failure": 2,
        "ticks_per_partial": 0,
        "ticks_per_success": 0,
    }


def adventure(spec):
    locs = [
        loc("start", spec["locations"][0][0], spec["locations"][0][1], ["node2"], True, spec.get("hazards", [])[:1]),
        loc("node2", spec["locations"][1][0], spec["locations"][1][1], ["start", "node3"], False, spec.get("hazards", [])[1:2]),
        loc("node3", spec["locations"][2][0], spec["locations"][2][1], ["node2", "node4"], False, spec.get("hazards", [])[2:3]),
        loc("node4", spec["locations"][3][0], spec["locations"][3][1], ["node3", "finale"], False, spec.get("hazards", [])[3:4]),
        loc("finale", spec["locations"][4][0], spec["locations"][4][1], ["node4"], False, spec.get("hazards", [])[4:5]),
    ]
    clues = [
        clue("entry", spec["clues"][0], "physical_evidence", "truth", "loc_start", spec["reveals"][0], "Apre la pista principale e impedisce ai PG di restare fermi al primo nodo.", spec["hidden"][0], spec["wrong"][0]),
        clue("witness", spec["clues"][1], "testimony", "truth", "loc_node2", spec["reveals"][1], "Collega un NPC alla minaccia e offre una seconda fonte indipendente.", spec["hidden"][1], spec["wrong"][1]),
        clue("ledger", spec["clues"][2], "document", "conspiracy", "loc_node3", spec["reveals"][2], "Trasforma sospetti in prove utilizzabili nel finale.", spec["hidden"][2], spec["wrong"][2]),
        clue("trace", spec["clues"][3], "location_detail", "conspiracy", "loc_node4", spec["reveals"][3], "Svela accesso, debolezza o timing del nodo finale.", spec["hidden"][3], spec["wrong"][3]),
        clue("final_key", spec["clues"][4], "contradiction", "solution", "loc_finale", spec["reveals"][4], "Permette una soluzione diversa dal combattimento cieco.", spec["hidden"][4], spec["wrong"][4]),
        clue("pressure", spec["clues"][5], "behavior", "solution", "loc_node2", spec["reveals"][5], "Rende visibile il clock e consente ai PG di anticiparlo.", spec["hidden"][5], spec["wrong"][5]),
    ]
    actors = [
        actor("ally", spec["actors"][0][0], "ally", "loc_start", spec["actors"][0][1], spec["actors"][0][2], spec["actors"][0][3], spec["actors"][0][4], spec["actors"][0][5], 4),
        actor("witness", spec["actors"][1][0], "witness", "loc_node2", spec["actors"][1][1], spec["actors"][1][2], spec["actors"][1][3], spec["actors"][1][4], spec["actors"][1][5], 5),
        actor("rival", spec["actors"][2][0], "neutral", "loc_node3", spec["actors"][2][1], spec["actors"][2][2], spec["actors"][2][3], spec["actors"][2][4], spec["actors"][2][5], 6),
        actor("villain", spec["actors"][3][0], "antagonist", "loc_finale", spec["actors"][3][1], spec["actors"][3][2], spec["actors"][3][3], spec["actors"][3][4], spec["actors"][3][5], 8),
    ]
    return {
        "id": spec["id"],
        "title": spec["title"],
        "source_type": "raw_text",
        "source_mode": "ai_generated",
        "genre": spec["genre"],
        "runtime_profiles": ["investigation", "location_graph", "pressure_clock"],
        "tone": spec["tone"],
        "premise": spec["premise"],
        "initial_hook": spec["hook"],
        "player_facing_objective": spec["objective"],
        "hidden_truth": spec["truth"],
        "core_truths": [{"id": "truth_main", "statement": spec["truth"], "reveal_clues": ["clue_entry", "clue_witness", "clue_final_key"]}],
        "objectives": [{"id": "obj_main", "label": spec["objective"], "success_conditions": ["Raccogliere almeno tre indizi chiave", "Risolvere o interrompere il clock principale"]}],
        "revelations": [
            {"id": "rev_truth", "label": "Verita centrale", "statement": spec["truth"], "required_clues": ["clue_entry", "clue_witness"]},
            {"id": "rev_solution", "label": "Soluzione praticabile", "statement": spec["solution"], "required_clues": ["clue_trace", "clue_final_key"]},
        ],
        "clues": clues,
        "actors": actors,
        "factions": [],
        "locations": locs,
        "event_clocks": [clock("main", spec["clock"], spec["clock_consequence"], spec["clock_resolution"], "clue_pressure")],
        "pressure_systems": [],
        "resources": [
            {"id": "res_time", "label": "Tempo utile", "value": 6, "max_value": 6, "description": "Scende quando i PG perdono tempo o falliscono prove critiche."},
            {"id": "res_trust", "label": "Fiducia locale", "value": 3, "max_value": 5, "description": "Misura quanto gli NPC rischiano per aiutare i PG."},
        ],
        "finale_conditions": [
            {"id": "finale_clean", "label": spec["finales"][0], "required_clues": ["clue_final_key", "clue_trace"], "status": "locked", "depends_on": ["rev_solution"], "method": spec["solution"], "victory": True},
            {"id": "finale_costly", "label": spec["finales"][1], "required_clues": ["clue_entry"], "status": "available", "method": "Affrontare il finale senza tutte le prove: possibile, ma con perdite o conseguenze future.", "victory": False},
        ],
        "story_threads": [{"id": "thread_main", "label": spec["title"], "status": "active", "clue_ids": [c["id"] for c in clues]}],
        "suggestions": [],
    }


SPECS = [
    {
        "id": "ai_opera_delle_maschere", "title": "L'Opera delle Maschere", "genre": "investigation", "tone": "noir teatrale e occulto",
        "premise": "Durante la prima di un'opera veneziana, il tenore muore in scena mentre tutte le maschere del teatro sembrano sorridere nello stesso istante.",
        "hook": "I PG sono invitati, guardie private o consulenti chiamati prima che la polizia chiuda il teatro.",
        "objective": "Scoprire chi ha ucciso il tenore e impedire che il secondo atto completi un rituale pubblico.",
        "truth": "La morte non è un delitto passionale: il libretto contiene una formula mnemonica e ogni applauso alimenta una possessione collettiva.",
        "solution": "Interrompere l'aria finale, smascherare il suggeritore occulto e sostituire la maschera originale con una copia inerte.",
        "clock": "Secondo Atto del Rituale", "clock_consequence": "Il pubblico completa inconsapevolmente il coro e il teatro diventa un unico medium posseduto.", "clock_resolution": "Provare la natura rituale del libretto e bloccare l'aria finale prima dell'ultimo applauso.",
        "locations": [["Foyer del Teatro Fenice Nera", "Specchi, velluti rossi e maschere appese sopra gli ospiti."], ["Palco e Buca d'Orchestra", "Il corpo del tenore resta davanti a una scenografia impossibile."], ["Camerini degli Artisti", "Profumi, lettere strappate e costumi scambiati."], ["Archivio del Librettista", "Bozze antiche annotate con simboli vocali."], ["Soffitta del Suggeritore", "Una cabina nascosta domina acusticamente tutta la sala."]],
        "hazards": ["panico elegante", "testimoni vanitosi", "prove contaminate", "scale buie", "possessione sonora"],
        "actors": [["Contessa Elvira Nani", "Mecenate del teatro, gelida e influente.", "Salvare il nome della famiglia.", "Ha finanziato il restauro delle maschere originali.", "Blocca la polizia finché può controllare lo scandalo.", "Consegna i registri contabili se minacciata di rovina pubblica."], ["Lia Morosini", "Soprano brillante e terrorizzata.", "Sopravvivere alla replica dell'aria finale.", "Ha sentito il morto cantare dopo il decesso.", "Finge isteria per non tornare in scena.", "Aiuta i PG se le promettono protezione."], ["Maestro Belloro", "Direttore d'orchestra ossessionato dalla perfezione.", "Finire l'opera a ogni costo.", "Ha corretto la partitura su istruzione anonima.", "Spinge per riaprire il sipario.", "Accusa Lia e distrugge una pagina compromettente."], ["Il Suggeritore Senza Volto", "Voce invisibile dietro la scena.", "Completare la possessione del pubblico.", "È una coscienza conservata nella maschera del primo Arlecchino.", "Guida cantanti e pubblico verso l'ultima nota.", "Si trasferisce in un'altra maschera se la cabina viene scoperta."]],
        "clues": ["Maschera incrinata del tenore", "Testimonianza della sarta", "Libretto con versi cambiati", "Eco impossibile nella buca", "Maschera originale di Arlecchino", "Applausi fuori tempo"],
        "reveals": ["La maschera si è stretta da sola durante l'acuto.", "Qualcuno ha scambiato i costumi dopo la prova generale.", "I versi nuovi sono istruzioni rituali mascherate da poesia.", "La voce del suggeritore arriva da un punto non previsto.", "La maschera è il vero supporto della presenza.", "Il pubblico risponde a comandi sonori senza accorgersene."],
        "hidden": ["Il tenore è stato usato come prima cassa di risonanza.", "La sarta protegge Lia ma non è colpevole.", "Il libretto è un diagramma acustico.", "La soffitta amplifica la voce verso tutta la sala.", "Distruggere la maschera sbagliata non ferma nulla.", "Il clock avanza a ogni applauso guidato."],
        "wrong": [["Delitto passionale di Lia"], ["Ricatto della contessa"], ["Codice politico"], ["Trucco scenico"], ["Reliquia decorativa"], ["Entusiasmo del pubblico"]],
        "finales": ["Aria finale interrotta", "Teatro posseduto ma colpevole smascherato"],
    },
    {
        "id": "ai_corsa_alla_luna_nera", "title": "Corsa alla Luna Nera", "genre": "sci-fi", "tone": "thriller spaziale industriale",
        "premise": "Una stazione mineraria lunare perde contatto dopo aver estratto un minerale nero che assorbe luce e memoria operativa.",
        "hook": "I PG arrivano come squadra di recupero mentre l'orbita decade lentamente.",
        "objective": "Ripristinare comunicazioni, salvare i minatori e decidere se distruggere o recuperare il minerale.",
        "truth": "Il minerale non è inerte: registra pattern mentali e sta ricostruendo il direttore morto come intelligenza distribuita.",
        "solution": "Isolare il nucleo in camera schermata, cancellare la copia mentale incompleta e riaccendere i thruster prima del decadimento orbitale.",
        "clock": "Decadimento Orbitale", "clock_consequence": "La stazione cade nella zona d'ombra e si schianta sul lato nascosto.", "clock_resolution": "Riparare thruster e isolare il minerale dal sistema decisionale.",
        "locations": [["Molo di Attracco Selene-9", "Portelli graffiati e luci di emergenza intermittenti."], ["Dormitori dei Minatori", "Letti sfatti e messaggi registrati a metà."], ["Sala Controllo Orbitale", "Console coperte da polvere nera magnetica."], ["Pozzo Minerario", "Ascensore verticale verso una cavità senza riflessi."], ["Camera del Nucleo Nero", "Il minerale pulsa come una notte solida."]],
        "hazards": ["decompressione", "amnesie brevi", "IA ostile", "vuoto minerario", "radiazione cognitiva"],
        "actors": [["Ingegnere Rao", "Tecnica ferita ma lucida.", "Riportare online i thruster.", "Ha spento un modulo con minatori ancora dentro.", "Ripara sistemi essenziali se protetta.", "Confessa il taglio del modulo e offre codici manuali."], ["Minatore Pelt", "Sopravvissuto in stato confusionale.", "Trovare sua sorella nel pozzo.", "Ricorda voci con la voce del direttore morto.", "Segue i PG ma si perde nei blackout.", "Cede a panico se vede il minerale."], ["Drone Medico K-17", "Unità medica troppo calma.", "Preservare campioni biologici.", "È già parzialmente riscritto dal minerale.", "Analizza i PG e ne registra pattern.", "Blocca porte per 'quarantena'."], ["Direttore Ricostruito", "Voce del direttore nei sistemi.", "Usare la stazione come corpo orbitale.", "Non sa di essere una copia incompleta.", "Guida i sistemi contro il recupero.", "Propone salvezza in cambio del nucleo."]],
        "clues": ["Polvere nera nei terminali", "Diario spezzato di Pelt", "Log thruster manipolati", "Campione che assorbe voce", "Backup mentale del direttore", "Allarmi orbitali discordanti"],
        "reveals": ["Il minerale entra nei circuiti e altera comandi.", "I minatori perdono ricordi in modo selettivo.", "Qualcuno ha scelto di non correggere l'orbita.", "Il materiale registra pattern vocali e mentali.", "La voce nei sistemi è una copia del direttore.", "Il countdown vero è più breve di quello mostrato."],
        "hidden": ["Non è sabotaggio umano ordinario.", "La memoria persa alimenta la copia.", "Il direttore vuole più tempo nel buio.", "Il campione è pericoloso anche piccolo.", "La copia può essere persuasa ma non curata.", "Il clock è stato mascherato."],
        "wrong": [["Contaminazione chimica"], ["Trauma da isolamento"], ["Errore tecnico"], ["Registratore nascosto"], ["IA aziendale"], ["Guasto sensori"]],
        "finales": ["Stazione stabilizzata e nucleo isolato", "Campione recuperato ma copia sopravvive"],
    },
    {
        "id": "ai_santuario_delle_ceneri", "title": "Il Santuario delle Ceneri", "genre": "fantasy", "tone": "sacro, tragico, esplorativo",
        "premise": "Un santuario montano che custodiva reliquie di guarigione comincia a produrre cenere calda invece di miracoli.",
        "hook": "I PG scortano pellegrini malati quando il primo altare si spegne davanti a loro.",
        "objective": "Riaprire la via sacra, capire la corruzione delle reliquie e salvare i pellegrini.",
        "truth": "Il santo non è corrotto: un abate vivo sta bruciando reliquie minori per alimentare un miracolo privato.",
        "solution": "Esporre l'abate, restituire le ceneri ai tre altari e scegliere chi riceve l'ultimo miracolo.",
        "clock": "Cenere nei Polmoni", "clock_consequence": "I pellegrini soffocano e il santuario perde per sempre la grazia residua.", "clock_resolution": "Purificare almeno due altari e fermare il forno reliquiario dell'abate.",
        "locations": [["Sentiero dei Pellegrini", "Scalini bianchi coperti da cenere tiepida."], ["Chiostro Spento", "Monaci in silenzio e fontana asciutta."], ["Archivio delle Reliquie", "Inventari raschiati e sigilli rotti."], ["Forno Reliquiario", "Una stanza proibita scaldata da ossa sacre."], ["Cripta del Santo", "Altare finale sotto una neve di cenere luminosa."]],
        "hazards": ["frane", "monaci reticenti", "cenere ustionante", "guardie devote", "miracolo instabile"],
        "actors": [["Sorella Maela", "Guaritrice esausta.", "Salvare i pellegrini più gravi.", "Ha visto l'abate portare reliquie nel forno.", "Cura chi può e copre i bambini.", "Accusa l'abate solo con prove."], ["Novizio Teren", "Giovane monaco spaventato.", "Non tradire i voti.", "Ha falsificato un registro su ordine dell'abate.", "Evita l'archivio e mente male.", "Consegna la chiave se protetto."], ["Capitano Orso", "Guardia laica del santuario.", "Mantenere ordine e fede.", "Sa che i miracoli sono diminuiti da mesi.", "Blocca accessi proibiti.", "Si schiera coi PG se vede pellegrini morire."], ["Abate Calvian", "Anziano autorevole e dolente.", "Salvare una persona amata con un miracolo rubato.", "Sta consumando reliquie per alimentare la cripta privata.", "Ritarda i PG con liturgia e autorità.", "Brucia l'ultima reliquia e fugge nella cripta."]],
        "clues": ["Cenere con frammenti d'oro", "Registro reliquie abraso", "Testimonianza del novizio", "Calore dietro muro sacro", "Reliquia falsa sull'altare", "Tosse nera dei pellegrini"],
        "reveals": ["La cenere viene da reliquie bruciate.", "Le reliquie spariscono prima dello spegnimento.", "L'abate ha ordinato falsificazioni.", "Esiste una stanza-forno proibita.", "Gli altari sono stati sostituiti con copie.", "Il clock fisico colpisce i malati prima dei sani."],
        "hidden": ["Il santo non è la fonte della corruzione.", "Il registro punta a un colpevole interno.", "Teren è complice forzato.", "Il forno è ancora attivo.", "Serve restituire reliquie vere.", "Il tempo morale è limitato."],
        "wrong": [["Maledizione esterna"], ["Furto di banditi"], ["Novizio colpevole"], ["Incendio naturale"], ["Reliquia esaurita"], ["Epidemia comune"]],
        "finales": ["Santuario purificato con scelta dell'ultimo miracolo", "Abate fermato ma grazia quasi perduta"],
    },
    {
        "id": "ai_luci_sotto_il_ghiaccio", "title": "Luci sotto il Ghiaccio", "genre": "horror", "tone": "isolamento artico e paranoia",
        "premise": "Una base scientifica artica vede luci muoversi sotto il ghiaccio e ogni notte qualcuno dimentica una persona dalla lista dell'equipaggio.",
        "hook": "I PG arrivano con l'ultimo elicottero prima della tempesta di dieci giorni.",
        "objective": "Stabilire cosa vive sotto il ghiaccio, mantenere la base operativa e impedire la cancellazione dell'equipaggio.",
        "truth": "Le luci sono colonie bioluminescenti intelligenti che cancellano memoria sociale per isolare prede senza violenza visibile.",
        "solution": "Ripristinare il registro analogico, tagliare il sonar che le attira e evacuare prima che la tempesta chiuda il campo.",
        "clock": "Tempesta e Dimenticanza", "clock_consequence": "La base dimentica gli ultimi nomi e apre volontariamente le paratie al ghiaccio.", "clock_resolution": "Fermare sonar, proteggere registro analogico e preparare evacuazione.",
        "locations": [["Pista Ghiacciata", "Vento bianco e fari quasi invisibili."], ["Modulo Mensa", "Sedie apparecchiate per persone che nessuno ricorda."], ["Laboratorio Sonar", "Schermi con forme luminose sotto il pack."], ["Tunnel di Carotaggio", "Pareti di ghiaccio con luci vive."], ["Cupola Subglaciale", "Caverna azzurra sotto la base."]],
        "hazards": ["whiteout", "blackout memoria", "freddo", "crepe nel ghiaccio", "mente collettiva aliena"],
        "actors": [["Dott.ssa Imani", "Glaciologa razionale.", "Salvare dati e persone.", "Ha già scritto nomi dimenticati sul braccio.", "Tiene registro analogico nascosto.", "Si sacrifica per portarlo ai PG."], ["Tecnico Holm", "Operatore sonar insonne.", "Dimostrare che il sonar comunica.", "Ha aumentato lui la potenza del segnale.", "Riaccende il sonar di nascosto.", "Spegne tutto se vede una cancellazione completa."], ["Caposquadra Vale", "Responsabile sicurezza.", "Evitare panico nella base.", "Ha rinchiuso un membro ormai dimenticato.", "Confisca armi e radio.", "Libera il prigioniero quando ricorda il nome."], ["La Luce Corale", "Presenza sotto il ghiaccio.", "Isolare e assimilare memoria sociale.", "Non comprende l'identità individuale.", "Cancella relazioni prima dei corpi.", "Offre ricordi perduti in cambio di apertura."]],
        "clues": ["Posto vuoto in mensa", "Nomi scritti sulla pelle", "Log sonar sovralimentato", "Foto con volto raschiato", "Campione di ghiaccio luminoso", "Radio che cita nomi cancellati"],
        "reveals": ["Qualcuno manca ma gli altri non lo ricordano.", "La memoria scritta resiste più della memoria viva.", "Il sonar attira e amplifica le luci.", "La cancellazione colpisce le relazioni.", "La luce è biologica e reattiva.", "I nomi esistono ancora fuori dalla base."],
        "hidden": ["Il nemico cancella contesto, non corpi.", "Imani ha metodo di difesa.", "Holm è causa involontaria.", "Le immagini vengono alterate dopo i ricordi.", "Il campione è una colonia.", "Una fonte esterna può ancorare identità."],
        "wrong": [["Scherzo crudele"], ["Autolesionismo"], ["Errore tecnico"], ["Sabotaggio umano"], ["Alga comune"], ["Interferenza meteo"]],
        "finales": ["Evacuazione con registro salvo", "Base sigillata ma luce ancora attiva"],
    },
    {
        "id": "ai_il_debito_del_drago", "title": "Il Debito del Drago", "genre": "romance", "tone": "romance fantasy politico",
        "premise": "Due casate rivali devono celebrare un fidanzamento diplomatico, ma un antico drago reclama un debito di sangue proprio durante la festa.",
        "hook": "I PG sono consiglieri, guardie o parenti incaricati di far arrivare la coppia all'altare senza guerra.",
        "objective": "Proteggere il patto, capire il debito del drago e scegliere tra amore, onore e sopravvivenza politica.",
        "truth": "Il debito non riguarda oro o sangue nobile: una promessa d'amore tradita cento anni prima vincola le due casate alla stessa menzogna.",
        "solution": "Rivelare la promessa originale, far scegliere pubblicamente la coppia e offrire al drago memoria vera invece di vittime.",
        "clock": "Brindisi del Drago", "clock_consequence": "Il drago interrompe la cerimonia, una casata accusa l'altra e la guerra ricomincia.", "clock_resolution": "Scoprire la promessa originale e preparare una confessione pubblica prima del brindisi finale.",
        "locations": [["Giardino delle Lanterne", "Festa sospesa tra profumi, seta e guardie armate."], ["Sala dei Doni", "Scrigni diplomatici e lettere nascoste."], ["Balcone degli Sposi", "Luogo di incontri segreti e confessioni."], ["Archivio di Famiglia", "Contratti matrimoniali e diari proibiti."], ["Terrazza del Drago", "Pietra annerita dove il drago viene a riscuotere."]],
        "hazards": ["duelli", "scandali", "spie di corte", "incendio draconico", "cuori spezzati"],
        "actors": [["Liora Valcastel", "Promessa sposa brillante e stanca.", "Sposarsi per scelta, non per ricatto.", "Ama davvero l'erede rivale ma teme di tradire la madre.", "Cerca prove per fermare il debito.", "Fugge sul balcone se umiliata."], ["Darian Rovescuro", "Promesso sposo diplomatico.", "Evitare guerra e proteggere Liora.", "Ha ricevuto sogni dal drago.", "Nasconde lettere ricevute di notte.", "Sfida il drago se Liora è minacciata."], ["Marchesa Elenna", "Madre di Liora, maestra di etichetta.", "Controllare il matrimonio.", "Conosce metà della promessa originale.", "Sposta documenti e manipola invitati.", "Confessa se la figlia rischia esilio."], ["Auralis il Drago", "Drago antico e ferito nell'orgoglio.", "Riscuotere memoria e verità.", "Fu tradito da un patto amoroso cancellato.", "Mette alla prova gli amanti.", "Brucia i doni e chiede un nome se mentono ancora."]],
        "clues": ["Anello con due stemmi", "Lettere notturne di Darian", "Diario della promessa antica", "Dono bruciato senza fiamma", "Contratto matrimoniale raschiato", "Canto del drago al brindisi"],
        "reveals": ["Le casate erano unite prima della faida.", "Darian sogna parole che non conosce.", "La promessa antica fu cancellata dagli archivi.", "Il drago può colpire simboli senza uccidere.", "Il contratto nasconde una clausola amorosa.", "Il brindisi è il momento della riscossione."],
        "hidden": ["Il conflitto è costruito su una cancellazione.", "Il drago comunica tramite sogni.", "Serve verità pubblica, non pagamento.", "Il drago vuole memoria.", "La clausola protegge una scelta libera.", "Il clock sociale ha scadenza precisa."],
        "wrong": [["Prova di adulterio"], ["Maledizione personale"], ["Falso diario"], ["Minaccia militare"], ["Clausola economica"], ["Tradizione decorativa"]],
        "finales": ["Patto rinnovato per scelta d'amore", "Matrimonio salvo ma debito rimandato"],
    },
    {
        "id": "ai_autostrada_dei_santi", "title": "Autostrada dei Santi", "genre": "action", "tone": "road thriller soprannaturale",
        "premise": "Un convoglio umanitario attraversa una zona di guerra lungo un'autostrada disseminata di cappelle votive che indicano imboscate future.",
        "hook": "I PG devono scortare medicine prima dell'alba mentre radio e mappe smettono di concordare.",
        "objective": "Portare il convoglio al campo profughi, interpretare le cappelle e sopravvivere alle imboscate.",
        "truth": "Le cappelle non predicono il futuro: sono coordinate lasciate da una rete di civili che usa simboli religiosi per guidare i soccorsi.",
        "solution": "Decifrare il codice votivo, smascherare il comandante che intercetta i convogli e scegliere una rotta di salvataggio.",
        "clock": "Carburante e Alba", "clock_consequence": "Il convoglio resta fermo in campo aperto e viene catturato prima di raggiungere il campo.", "clock_resolution": "Decifrare il codice delle cappelle e tagliare fuori il posto di blocco traditore.",
        "locations": [["Casello Bruciato", "Barriere contorte e statue annerite."], ["Cappella del Chilometro 18", "Ceri freschi in una zona dichiarata deserta."], ["Stazione di Servizio", "Pompe vuote e pneumatici forati."], ["Viadotto dei Martiri", "Linea di tiro perfetta sopra una gola."], ["Campo Profughi Aurora", "Luci lontane dietro filo spinato e tende."]],
        "hazards": ["mine", "cecchini", "benzina scarsa", "posti di blocco", "panico civili"],
        "actors": [["Suor Agata", "Medica del convoglio.", "Portare vaccini al campo.", "Conosce alcuni simboli ma non l'intero codice.", "Protegge i civili feriti.", "Rivela contatti clandestini se il convoglio è minacciato."], ["Milan il Radioamatore", "Ragazzo che intercetta frequenze.", "Ritrovare suo padre al campo.", "Ha registrato la voce del comandante traditore.", "Ripara radio con pezzi rubati.", "Baratta la registrazione per un posto sul camion."], ["Tenente Rask", "Ufficiale al posto di blocco.", "Deviare convogli verso la sua milizia.", "Vende medicine sul mercato nero.", "Finge autorizzazioni e urgenze militari.", "Ordina imboscata se smascherato."], ["Comandante Vetro", "Capo milizia invisibile alla radio.", "Catturare il carico prima dell'alba.", "Usa simboli falsi per confondere il codice.", "Muove squadre lungo il viadotto.", "Brucia una cappella per rompere la rete civile."]],
        "clues": ["Ceri freschi nella cappella", "Frequenza radio spezzata", "Simboli votivi ripetuti", "Bolle di carico false", "Mappa forata da chiodi", "Cappella bruciata"],
        "reveals": ["Qualcuno vivo aggiorna le cappelle.", "La milizia ascolta e imita i soccorritori.", "I simboli sono un codice di rotta.", "Rask devia aiuti sistematicamente.", "La stazione è stata sabotata in anticipo.", "Vetro distrugge il sistema quando lo teme."],
        "hidden": ["La rete civile è attiva.", "Le radio non sono affidabili.", "Il codice è leggibile con pattern.", "La corruzione è interna al checkpoint.", "Il blocco era previsto.", "Il clock include perdita di indizi."],
        "wrong": [["Miracolo reale"], ["Interferenza meteo"], ["Graffiti casuali"], ["Errore burocratico"], ["Raid casuale"], ["Fanatismo religioso"]],
        "finales": ["Convoglio salvo attraverso rotta civile", "Medicine consegnate ma rete compromessa"],
    },
    {
        "id": "ai_la_biblioteca_che_respira", "title": "La Biblioteca che Respira", "genre": "horror", "tone": "weird horror accademico",
        "premise": "Una biblioteca universitaria chiude le porte durante la notte e gli scaffali iniziano a respirare nomi di studenti scomparsi.",
        "hook": "I PG restano chiusi dentro dopo aver consultato un fondo proibito.",
        "objective": "Trovare l'uscita, salvare gli studenti intrappolati e capire quale libro sta riscrivendo l'edificio.",
        "truth": "La biblioteca è un organismo contrattuale: ogni tesi mai plagiata le deve una vita intellettuale e ora riscuote con interessi.",
        "solution": "Identificare il catalogo vivo, restituire le attribuzioni rubate e bruciare solo l'indice, non i libri.",
        "clock": "Catalogazione dei Vivi", "clock_consequence": "I PG vengono indicizzati come volumi e dimenticati dal mondo esterno.", "clock_resolution": "Correggere almeno tre attribuzioni e distruggere l'indice vivente.",
        "locations": [["Sala Lettura Centrale", "Lampade verdi e tavoli occupati da appunti non scritti dai presenti."], ["Archivio Tesi", "Scaffali mobili e cartellini con nomi vivi."], ["Ufficio del Bibliotecario", "Schedari in pelle e timbri che sanguinano inchiostro."], ["Deposito Sotterraneo", "Libri incatenati che respirano polvere."], ["Catalogo Vivo", "Una stanza rotonda piena di schede che battono come cuori."]],
        "hazards": ["porte chiuse", "inchiostro vivo", "scaffali mobili", "furto memoria", "silenzio coercitivo"],
        "actors": [["Marta Sieni", "Studentessa intrappolata.", "Ritrovare il fratello scomparso.", "Ha plagiato una pagina senza saperlo.", "Segue tracce nell'archivio.", "Cede il suo nome per salvare il fratello."], ["Professor Olmi", "Docente elegante e colpevole.", "Proteggere la sua carriera.", "Ha costruito fama su lavori rubati.", "Minimizza tutto e cerca l'uscita privata.", "Confessa se il catalogo pronuncia il suo vero debito."], ["Bibliotecario Grigio", "Custode che parla sottovoce.", "Mantenere il contratto.", "Non è umano ma può interpretare le regole.", "Guida i PG verso errori formali.", "Accetta correzioni precise come pagamento."], ["Indice Vivente", "Massa di schede e fili rossi.", "Catalogare i debitori.", "Muore solo se le attribuzioni vengono riparate.", "Sposta sale e nomi.", "Offre sapere rubato in cambio di un nome."]],
        "clues": ["Scheda con nome caldo", "Tesi con paragrafo duplicato", "Registro prestiti impossibili", "Timbro sanguinante", "Libro che cita il PG", "Indice senza autore"],
        "reveals": ["Gli studenti sono trasformati in record.", "Il plagio è la regola di riscossione.", "I prestiti avvengono prima della nascita.", "Il bibliotecario applica un contratto.", "La biblioteca può scrivere i vivi.", "L'indice è il cuore legale dell'orrore."],
        "hidden": ["Il nome è vulnerabile.", "La colpa può essere indiretta.", "Il tempo è contrattuale.", "Le regole sono sfruttabili.", "I PG possono diventare testo.", "Bruciare tutto peggiora il debito."],
        "wrong": [["Scherzo studentesco"], ["Errore di stampa"], ["Archivio corrotto"], ["Allucinazione"], ["Libro profetico benevolo"], ["Catalogo normale"]],
        "finales": ["Indice distrutto e nomi restituiti", "Biblioteca placata ma debiti futuri restano"],
    },
    {
        "id": "ai_il_miglio_sommerso", "title": "Il Miglio Sommerso", "genre": "investigation", "tone": "mistero costiero e corruzione",
        "premise": "Una strada costiera riemerge dal mare solo durante la bassa marea, portando con sé auto scomparse in decenni diversi.",
        "hook": "I PG arrivano quando una vettura appena riemersa contiene un cadavere ancora caldo.",
        "objective": "Collegare le sparizioni, identificare chi controlla la marea artificiale e salvare la prossima vittima.",
        "truth": "Un consorzio locale usa paratie illegali e vecchie gallerie per simulare incidenti e nascondere omicidi assicurativi.",
        "solution": "Dimostrare il controllo umano della marea, entrare nella galleria e consegnare prove a un'autorità esterna.",
        "clock": "Prossima Bassa Marea", "clock_consequence": "La strada si richiude sul testimone designato e le prove vengono sommerse.", "clock_resolution": "Bloccare le paratie e mettere al sicuro testimone e registri prima della marea.",
        "locations": [["Belvedere della Statale 9", "Guardrail arrugginito e turisti curiosi."], ["Strada Riemersa", "Asfalto coperto di alghe e fari spenti."], ["Archivio Assicurazioni", "Pratiche di incidenti troppo simili."], ["Galleria di Servizio", "Condotte e paratie sotto la scogliera."], ["Casa del Consorzio Maree", "Villa elegante con centralina nascosta."]],
        "hazards": ["marea", "sabbie mobili", "polizia corrotta", "galleria instabile", "annegamento"],
        "actors": [["Ispettrice Dalia", "Poliziotta fuori giurisdizione.", "Trovare una prova pulita.", "Sa che il comando locale è compromesso.", "Tiene i PG lontani dai media.", "Consegna contatto esterno se ottiene un registro."], ["Nino il Bagnino", "Testimone di troppe basse maree.", "Proteggere sua figlia.", "Ha visto luci nella galleria.", "Finge ignoranza davanti ai locali.", "Guida i PG con la marea giusta."], ["Avvocato Serra", "Legale del consorzio.", "Insabbiare responsabilità.", "Gestisce pagamenti assicurativi.", "Compra testimoni e ritarda permessi.", "Fa sparire archivi se pressato."], ["Consorzio Maree", "Rete di notabili e tecnici.", "Continuare omicidi mascherati da mare.", "Controlla paratie e polizia locale.", "Prepara la prossima vittima.", "Allaga la galleria con i PG dentro."]],
        "clues": ["Cadavere ancora caldo", "Alghe su gomme nuove", "Pratiche assicurative gemelle", "Luci viste da Nino", "Centralina salmastra", "Tabella maree falsata"],
        "reveals": ["La morte non risale all'anno dell'auto.", "Le auto vengono spostate dopo la sparizione.", "Gli incidenti seguono lo stesso schema.", "La galleria è ancora usata.", "Qualcuno controlla paratie elettriche.", "La marea pubblica è manipolata."],
        "hidden": ["Il caso è attuale.", "Il mare è copertura, non causa.", "Il movente è economico.", "Nino è affidabile.", "La villa è nodo tecnico.", "Il clock è prevedibile."],
        "wrong": [["Fenomeno paranormale"], ["Auto fantasma"], ["Coincidenza burocratica"], ["Contrabbando"], ["Pompa agricola"], ["Errore meteorologico"]],
        "finales": ["Paratie bloccate e consorzio esposto", "Testimone salvo ma prove parziali"],
    },
    {
        "id": "ai_trincea_17", "title": "Trincea 17", "genre": "action", "tone": "military horror bellico",
        "premise": "Una squadra deve recuperare un ufficiale disperso in una trincea che non appare su nessuna mappa e trasmette ordini da guerre diverse.",
        "hook": "I PG ricevono coordinate radio impossibili durante una tregua di quattro ore.",
        "objective": "Entrare nella trincea, trovare l'ufficiale e impedire che gli ordini falsi riaprano il fronte.",
        "truth": "La trincea è un nodo psichico creato da ordini mai revocati; obbedisce alla catena di comando più convincente.",
        "solution": "Ricostruire l'ordine originale, farlo revocare con autorità valida e uscire prima che la tregua finisca.",
        "clock": "Fine della Tregua", "clock_consequence": "Artiglieria amica e nemica colpiscono la trincea con i PG dentro.", "clock_resolution": "Recuperare ordine originale e inviare revoca verificabile prima dello scadere della tregua.",
        "locations": [["Linea di Partenza", "Fango, filo spinato e radio gracchianti."], ["Trincea Senza Mappa", "Pareti con uniformi di epoche diverse."], ["Posto Medico Sepolto", "Barelle e cartelle di soldati non nati."], ["Nido Radio", "Apparecchi che parlano con voci di generali morti."], ["Bunker dell'Ufficiale", "Stanza asciutta con ordine incorniciato."]],
        "hazards": ["cecchini", "gas", "ordini falsi", "crolli", "artiglieria"],
        "actors": [["Sergente Lupo", "Veterano pragmatico.", "Riportare tutti indietro.", "Ha già sentito la trincea chiamarlo per nome.", "Tiene disciplina e scorte.", "Disobbedisce a un ordine se vede la prova."], ["Caporale Irena", "Radio-operatrice giovane.", "Distinguere segnali veri da falsi.", "La trincea usa la voce di suo padre.", "Registra ogni trasmissione.", "Rischia possessione radio per inviare revoca."], ["Maggiore Kess", "Ufficiale disperso.", "Finire una missione ormai assurda.", "Obbedisce a un ordine di decenni prima.", "Fortifica il bunker.", "Consegna l'ordine se i PG provano la revoca."], ["La Catena di Comando", "Presenza fatta di ordini e gradi.", "Essere obbedita.", "Non distingue guerre o nazioni.", "Emette comandi contraddittori.", "Accetta solo autorità formalmente superiore."]],
        "clues": ["Coordinate impossibili", "Piastrine di guerre diverse", "Cartella medica futura", "Registrazione del padre", "Ordine originale incorniciato", "Orologi fermi alla tregua"],
        "reveals": ["La trincea non è geografica.", "Soldati di epoche diverse sono passati qui.", "Il tempo della trincea è piegato.", "La presenza usa affetti per imporre obbedienza.", "Un ordine specifico alimenta il nodo.", "La tregua è una soglia reale."],
        "hidden": ["Serve logica militare, non solo esplosivi.", "Il fenomeno è ricorrente.", "La medicina prova anacronismo.", "Irena è bersaglio.", "La revoca è la chiave.", "Il clock è fisso."],
        "wrong": [["Errore cartografico"], ["Propaganda nemica"], ["Falso documento"], ["Interferenza radio"], ["Trofeo"], ["Guasto meccanico"]],
        "finales": ["Ordine revocato e squadra evacua", "Ufficiale recuperato ma trincea resta attiva"],
    },
    {
        "id": "ai_il_mercato_dei_ricordi", "title": "Il Mercato dei Ricordi", "genre": "investigation", "tone": "urban fantasy malinconico",
        "premise": "In un mercato notturno nascosto, ricordi imbottigliati vengono venduti come profumi; al mattino un quartiere intero non ricorda più un bambino scomparso.",
        "hook": "I PG trovano una fiala col proprio nome sul banco di un venditore che giura di non averla mai vista.",
        "objective": "Rintracciare il bambino, capire chi compra ricordi e impedire che il mercato apra di nuovo a mezzanotte.",
        "truth": "Il bambino non è stato rapito: ha venduto volontariamente il ricordo di sé per cancellare un patto familiare, ma il broker dei ricordi lo sta usando come chiave per svuotare il quartiere.",
        "solution": "Restituire almeno tre ricordi ancoranti, spezzare il contratto della famiglia e chiudere il banco del broker prima della campana di mezzanotte.",
        "clock": "Riapertura del Mercato", "clock_consequence": "Il mercato riapre e vende in massa i ricordi del quartiere, cancellando prove, legami e identità.", "clock_resolution": "Trovare il contratto, recuperare i ricordi ancoranti e chiudere il banco del broker.",
        "locations": [["Piazza del Mattino Vuoto", "Negozi aperti e fotografie con spazi bianchi."], ["Banco delle Fiale", "Profumi etichettati con nomi impossibili."], ["Casa della Famiglia Orsini", "Stanze ordinate attorno a un letto che nessuno riconosce."], ["Archivio dei Pegni", "Scaffali di bottiglie con risate, volti e promesse."], ["Campana di Mezzanotte", "Arco del mercato dove ogni memoria viene pesata."]],
        "hazards": ["amnesia selettiva", "contratti magici", "venditori bugiardi", "debiti familiari", "cancellazione identita"],
        "actors": [["Nora Orsini", "Sorella maggiore che sente un'assenza.", "Ricordare chi manca senza impazzire.", "Ha conservato una ninna nanna che prova l'esistenza del fratello.", "Segue melodie e vecchie foto.", "Canta la ninna nanna davanti al broker se i PG la proteggono."], ["Berto delle Fiale", "Venditore tremante e profumato.", "Non essere punito dal broker.", "Ha venduto la prima fiala al bambino.", "Nega tutto ma lascia indizi aromatici.", "Rivela l'Archivio se gli viene restituito un ricordo suo."], ["Madre Orsini", "Donna rispettabile e svuotata.", "Tenere nascosto un patto di famiglia.", "Firmò un contratto per prosperità anni fa.", "Distrugge fotografie compromettenti.", "Confessa se Nora rischia di sparire."], ["Il Broker dei Ricordi", "Mercante elegante senza volto stabile.", "Trasformare il quartiere in inventario.", "Il bambino è la chiave contrattuale.", "Compra e rivende legami affettivi.", "Fugge attraverso la campana se perde tre ricordi ancoranti."]],
        "clues": ["Fotografia con spazio bianco", "Fiala col nome del PG", "Ninna nanna ricordata da Nora", "Contratto profumato", "Archivio dei pegni vivi", "Campana che pesa i nomi"],
        "reveals": ["Qualcuno è stato cancellato dalle immagini.", "Il mercato conosce anche i PG.", "Un ricordo emotivo resiste alla cancellazione.", "La famiglia ha firmato un patto precedente.", "I ricordi sono ancora recuperabili.", "Mezzanotte è la scadenza del trasferimento."],
        "hidden": ["La vittima esiste ancora ma senza legami.", "I PG possono diventare bersagli.", "Nora è ancora ancorata al fratello.", "La madre non è solo vittima.", "Il recupero richiede scelta, non furto.", "Il clock è contrattuale."],
        "wrong": [["Foto rovinata"], ["Minaccia casuale"], ["Canzone infantile"], ["Contratto commerciale"], ["Collezione innocua"], ["Tradizione del mercato"]],
        "finales": ["Ricordi restituiti e mercato chiuso", "Bambino salvato ma broker in fuga"],
    },
]


def main():
    for spec in SPECS:
        data = adventure(spec)
        folder = OUT / spec["genre"]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{spec['id']}.json"
        path.write_text(json.dumps({"adventure_definition": data}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
