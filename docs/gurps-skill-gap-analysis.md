# Confronto Skill GURPS 4a Edizione / Motore Pandora Legio

Fonte confrontata: `/Users/stefan0/Desktop/SJG37-0201.pdf` (`Skill Categories`, GURPS 4a edizione).

Nota: il PDF organizza le abilita GURPS per categorie e include molte specializzazioni. Il motore attuale usa invece un catalogo compresso di 70 chiavi interne, tutte in italiano, con alcune macro-skill narrative. Questo significa che diverse abilita GURPS sono oggi assorbite da skill piu generiche.

## Stato Attuale Del Motore

Skill implementate: 70.

Per attributo interno:

- Forza: `combattere`, `resistere`, `forzare`, `proteggere`, `trasportare`, `intimidire`, `lottare`, `sopravvivere`, `demolire`, `nuotare`, `arrampicarsi`, `lanciare`, `sollevare`, `saltare`
- Agilita: `schivare`, `furtivita`, `acrobazia`, `rapidita`, `mira`, `guidare`, `manualita`, `infiltrarsi`, `scassinare`, `pedinare`, `cavalcare`, `mimetizzare`, `equilibrio`, `borseggiare`
- Intelligenza: `investigare`, `analizzare`, `tecnologia`, `medicina`, `cultura`, `strategia`, `decifrare`, `osservare`, `ingegneria`, `scienze`, `legge`, `occultismo`, `seguire_tracce`, `navigare`, `sopravvivenza_urbana`, `storia`, `economia`, `meccanica`, `elettronica`, `informatica`, `astronomia`, `biologia`, `chimica`, `fisica`, `linguistica`, `filosofia`, `teologia`, `politica`
- Empatia: `persuadere`, `ingannare`, `intuire`, `calmare`, `ispirare`, `curare`, `comandare`, `comunicare`, `intrattenere`, `etichetta`, `recitazione`, `parlare_in_pubblico`, `interrogare`, `seduzione`

## Skill GURPS Coperte Direttamente O Quasi Direttamente

Queste esistono nel motore con nome italiano uguale, equivalente o molto vicino:

- Acrobazia
- Arrampicarsi
- Astronomia
- Biologia
- Borseggio
- Cavalcare
- Chimica
- Diplomazia
- Economia
- Elettronica
- Esplosivi
- Fisica
- Furtivita
- Galateo
- Guidare / Pilotare
- Informatica
- Ingegneria
- Interrogatorio
- Intimidire
- Legge
- Leadership
- Linguistica
- Lottare
- Meccanica
- Medicina
- Mimetizzarsi
- Navigazione
- Nuotare
- Occultismo
- Osservare
- Parlare in Pubblico
- Psicologia
- Raggiro
- Recitazione
- Scassinare
- Seduzione
- Seguire Tracce
- Sopravvivenza
- Sopravvivenza Urbana
- Storia
- Tattica

## Skill GURPS Coperte Come Macro-Skill

Queste non esistono come abilita autonome, ma oggi vengono assorbite da una skill generica del motore:

- Armi da fuoco, arco, balestra, armi a energia, artiglieria, fionda, rete, lazo, cerbottana -> `mira`
- Ascia/mazza, spada, coltello, sciabola, lancia, bastone, frusta, tonfa, jitte/sai, kusari, garrota, armi a due mani -> `combattere`
- Pugilato, rissa, karate, judo, sumo, lotta -> `combattere` o `lottare`
- Entrata forzata, demolizione, sfondare, aprire a forza -> `forzare` o `demolire`
- Ricerca, criminologia, analisi informazioni, medicina legale, perquisire -> `investigare` o `analizzare`
- Operazione elettronica, uso computer, apparecchiature, sensori, terminali -> `tecnologia`, `elettronica`, `informatica`
- Conoscenza d'area, conoscenze correnti, sapere professionale, abilita esperta -> `cultura`
- Letteratura, antropologia, archeologia, sociologia, geografia -> `cultura`, `storia`, `filosofia`
- Cerimoniale religioso, rituale magico, taumaturgia, simboli magici, sapere nascosto -> `occultismo`, `teologia`, `decifrare`
- Travestimento, falsificazione, contraffazione, contrabbando, occultare oggetti -> `ingannare`, `manualita`, `borseggiare`
- Camuffamento, pedinamento, ombra, infiltrazione -> `furtivita`, `pedinare`, `mimetizzare`
- Primo soccorso, diagnosi, medico, chirurgia, fisiologia, veleni, farmacia -> `curare`, `medicina`, `biologia`, `chimica`
- Commercio, finanza, amministrazione, propaganda, politica -> `economia`, `politica`, `persuadere`
- Intrattenimento, canto, musica, poesia, recitazione, ventriloquia, trucco scenico -> `intrattenere`, `recitazione`

## Mancanti Come Skill Autonome

Se vogliamo una copertura piu fedele a GURPS 4a, queste andrebbero aggiunte come skill italiane distinte.

### Animali

- Addestrare Animali
- Falconeria
- Naturalista
- Imballaggio
- Conduzione Carri
- Veterinaria
- Mimetismo Animale

### Arti E Intrattenimento

- Arte
- Conoscitore
- Danza
- Mangiafuoco
- Esibizione di Gruppo
- Trucco
- Imitazione
- Composizione Musicale
- Strumento Musicale
- Fotografia
- Poesia
- Canto
- Prestidigitazione
- Combattimento Scenico
- Ventriloquia
- Scrittura

### Atletica

- Acrobazia Aerea
- Acrobazia Acquatica
- Bicicletta
- Senso Corporeo
- Controllo del Respiro
- Caduta Libera
- Escursionismo
- Paracadutismo
- Corsa
- Immersione
- Pattinaggio
- Sci
- Sport

### Affari

- Contabilita
- Amministrazione
- Finanza
- Analisi di Mercato
- Matematica
- Mercanteggiare
- Propaganda

### Combattimento

- Arte da Combattimento
- Sport da Combattimento
- Armi specifiche da mischia: ascia/mazza, spada larga, mantello, flagello, spada a forza, frusta a forza, garrota, jitte/sai, judo, karate, coltello, kusari, lancia da cavaliere, main-gauche, frusta monofilare, parata armi da lancio, arma in asta, striscia, sciabola, spada corta, spadino, lancia, bastone, sumo, tonfa, ascia/mazza a due mani, flagello a due mani, spada a due mani, frusta
- Armi specifiche a distanza: artiglieria, armi a energia, cerbottana, bolas, arco, balestra, caduta oggetti, estrazione rapida, cannoniere, armi da fuoco, attacco innato, lazo, proiettore liquido, rete, fionda, propulsore per lancia, arma da lancio

### Artigianato

- Carpenteria
- Oreficeria
- Lavorare il Cuoio
- Muratura
- Cucito
- Fabbro
- Arte: ceramica
- Arte: scultura
- Arte: lavorazione del legno

### Criminalita E Strada

- Bagordi
- Hackeraggio
- Contraffazione
- Travestimento
- Fuga
- Falsificazione
- Gioco d'Azzardo
- Nascondere Oggetti
- Mendicare
- Veleni
- Galateo Criminale
- Rovistare
- Contrabbando
- Trappole

### Progettazione E Invenzione

- Architettura
- Bioingegneria
- Programmazione
- Farmacia
- Scienza Bizzarra

### Esoteriche

- Autoipnosi
- Combattimento alla Cieca
- Controllo del Corpo
- Colpo Spezzante
- Sognare
- Incantamento Oratorio
- Medicina Esoterica
- Balzo Volante
- Posizione Immobile
- Arte dell'Invisibilita
- Kiai
- Passo Leggero
- Meditazione
- Forza Mentale
- Blocco Mentale
- Influenza Musicale
- Colpo di Potenza
- Punti di Pressione
- Segreti di Pressione
- Spinta
- Arte del Lancio
- Arcieria Zen

### Vita Quotidiana

- Conoscenza d'Area
- Uso Computer
- Cucina
- Faccende Domestiche
- Nodi
- Cucito
- Dattilografia
- Senso del Tempo Atmosferico

### Conoscenza

- Abilita Esperta
- Giochi
- Araldica
- Sapere Nascosto
- Hobby
- Abilita Professionale

### Medicina

- Diagnosi
- Medicina Esoterica
- Ipnotismo
- Farmacia
- Medico
- Fisiologia
- Veleni
- Chirurgia
- Veterinaria

### Militare

- Armeria
- Lavaggio del Cervello
- Camuffamento
- Osservatore Avanzato
- Analisi di Intelligence
- Tuta NBC
- Soldato

### Scienze Naturali

- Alchimia
- Abilita Esperta: epidemiologia
- Abilita Esperta: idrologia
- Abilita Esperta: filosofia naturale
- Geologia
- Matematica
- Metallurgia
- Meteorologia
- Naturalista
- Paleontologia
- Fisiologia

### Occulto E Magia

- Alchimia
- Esorcismo
- Abilita Esperta: psionica
- Erboristeria
- Sapere Nascosto: demoni
- Sapere Nascosto: fate
- Sapere Nascosto: spiriti
- Rituale Religioso
- Magia Rituale
- Disegno Simbolico
- Taumaturgia

### Esplorazione

- Camuffamento
- Cartografia
- Pesca
- Escursionismo
- Naturalista
- Prospezione
- Immersione
- Pattinaggio
- Sci
- Senso del Tempo Atmosferico

### Polizia

- Linguaggio del Corpo
- Criminologia
- Scoprire Bugie
- Medicina Legale
- Perquisire

### Riparazione E Manutenzione

- Armeria
- Elettricista
- Riparazione Elettronica
- Macchinista

### Studio

- Letteratura
- Ricerca
- Lettura Rapida
- Insegnamento
- Dattilografia
- Scrittura

### Sociale

- Linguaggio del Corpo
- Bagordi
- Conoscitore
- Scoprire Bugie
- Arte Erotica
- Divinazione
- Gesto
- Araldica
- Mercanteggiare
- Mendicare
- Insegnamento
- Vita di Strada

### Scienze Sociali E Umanistiche

- Antropologia
- Archeologia
- Cartografia
- Criminologia
- Geografia
- Letteratura
- Paleontologia
- Sociologia

### Spionaggio

- Hackeraggio
- Travestimento
- Guerra Elettronica
- Sicurezza Elettronica
- Sorveglianza Elettronica
- Fuga
- Abilita Esperta: sicurezza informatica
- Falsificazione
- Nascondere Oggetti
- Analisi di Intelligence
- Lettura Labbiale
- Fotografia
- Veleni
- Ricerca
- Perquisire
- Contrabbando

### Tecniche

- Tuta da Battaglia
- Uso Computer
- Tuta da Immersione
- Operazione Elettronica
- Movimentazione Carichi
- Materiali Pericolosi
- Matematica: rilevamento
- Tuta NBC
- Fotografia
- Dattilografia
- Tuta Spaziale

### Veicoli

- Aerostati
- Tuta da Battaglia
- Bicicletta
- Imbarcazioni
- Guidare
- Movimentazione Carichi
- Pilotare
- Marinaio
- Comando Nave
- Spaziale
- Sottomarino
- Equipaggio Sottomarino
- Conduzione Carri

## Differenza Importante

Il motore attuale non e ancora un catalogo GURPS completo. E un catalogo narrativo compatibile con tiri GURPS-lite:

- usa quattro attributi interni: Forza, Agilita, Intelligenza, Empatia
- traduce molte skill GURPS in macro-skill
- usa nomi italiani nelle chiavi interne e nella UI
- non distingue molte specializzazioni GURPS, soprattutto armi, tecnica, esoteriche, conoscenze e veicoli

## Regole GURPS Lite Verificate Nel Motore

Aggiornamento: il motore ora rispetta questi punti della regola base sulle abilita:

- tiro abilita: `3d6 <= abilita_effettiva`
- tiro 17 o 18: fallimento secondo la logica GURPS Lite gia presente nel motore
- attributo cardine per ogni skill: definito in `SKILL_INFO`
- difficolta skill: Facile / Media / Difficile, codificate come `E`, `M`, `D`
- valore minimo senza addestramento: attributo cardine -4/-5/-6
- Regola del 20: per i valori minimi, l'attributo cardine viene cappato a 20
- tabella costi abilita: corretta secondo la tabella GURPS Lite italiana
- flag iniziale per abilita tecnologiche `/LT`: presente per le macro-skill tecniche attuali

Limiti ancora aperti:

- `empatia` e una chiave storica del codice usata per visualizzare/gestire `SA`; in GURPS SA e Salute, non empatia emotiva. La UI e alcune skill sociali la usano ancora in senso narrativo, quindi va rinominata o separata in una passata dedicata.
- Le abilita senza valore minimo esistono nella regola, ma il catalogo compresso attuale non le distingue ancora in modo affidabile.
- Le abilita `/LT` sono solo segnalate come tecnologiche; non viene ancora salvato il livello tecnologico specifico sulla scheda, per esempio `Navigazione/LT2` contro `Navigazione/LT8`.
- Le specializzazioni GURPS non sono ancora modellate come skill autonome; molte restano sotto macro-skill.

## Raccomandazione

Prossimo passo consigliato:

1. Mantenere le macro-skill per la UI semplice.
2. Aggiungere un catalogo `gurps_skill_catalog_it` completo, in italiano, con alias inglese -> italiano.
3. Far scegliere all'engine una skill italiana specifica quando l'azione e chiara.
4. Se la skill specifica non e presente sulla scheda del personaggio, usare il default GURPS.
5. Mostrare in UI sempre il nome italiano, mai quello inglese.

Esempio:

- azione: "sparare con il fucile"
- skill specifica: `armi_da_fuoco`
- macro-effetto: `combattere`
- UI: "Armi da Fuoco"
- fallback narrativo se manca la skill: Agilita - penalita da difficolta
