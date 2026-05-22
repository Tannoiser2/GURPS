export const TILE_CATALOG = {
  sci_fi: {
    fog: ["/map-tiles/sci_fi/FOG_01.png"],
    reactor: ["/map-tiles/sci_fi/reactor_01.png", "/map-tiles/sci_fi/reactor_01.svg"],
    control: ["/map-tiles/sci_fi/control_01.png", "/map-tiles/sci_fi/control_01.svg"],
    communications: ["/map-tiles/sci_fi/communication_room_01.png", "/map-tiles/sci_fi/control_01.png", "/map-tiles/sci_fi/control_01.svg"],
    command_bridge: ["/map-tiles/sci_fi/command_bridge_01.png", "/map-tiles/sci_fi/control_01.png", "/map-tiles/sci_fi/control_01.svg"],
    server: ["/map-tiles/sci_fi/Server_centrale_01.png", "/map-tiles/sci_fi/control_01.png", "/map-tiles/sci_fi/control_01.svg"],
    medical: ["/map-tiles/sci_fi/medical_01.png", "/map-tiles/sci_fi/medical_01.svg"],
    cryo: ["/map-tiles/sci_fi/cryogenic_room_01.png", "/map-tiles/sci_fi/medical_01.png", "/map-tiles/sci_fi/medical_01.svg"],
    hangar: ["/map-tiles/sci_fi/hangar_01.png", "/map-tiles/sci_fi/hangar_01.svg"],
    lab: ["/map-tiles/sci_fi/lab_01.png", "/map-tiles/sci_fi/lab_01.svg"],
    archive: ["/map-tiles/sci_fi/archive_01.png", "/map-tiles/sci_fi/archive_01.svg"],
    cafeteria: ["/map-tiles/sci_fi/Mensa_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
    quarters: ["/map-tiles/sci_fi/quarters_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
    recreation: ["/map-tiles/sci_fi/recreation_room_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
    greenhouse: ["/map-tiles/sci_fi/greenhouse_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
    connector: ["/map-tiles/sci_fi/connector_01.png", "/map-tiles/sci_fi/connector_01.svg"],
    technical_corridor: ["/map-tiles/sci_fi/technical_corridor_01.png", "/map-tiles/sci_fi/connector_01.png", "/map-tiles/sci_fi/connector_01.svg"],
    storage: ["/map-tiles/sci_fi/storage_01.png", "/map-tiles/sci_fi/storage_01.svg"],
    tech: ["/map-tiles/sci_fi/tech_01.png", "/map-tiles/sci_fi/tech_01.svg"],
    training: ["/map-tiles/sci_fi/Palestra_tecnologica_01.png", "/map-tiles/sci_fi/tech_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
    fortified: ["/map-tiles/sci_fi/fortified_room_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
    room: ["/map-tiles/sci_fi/Stanza_generica_01.png", "/map-tiles/sci_fi/room_01.png", "/map-tiles/sci_fi/room_01.svg"],
  },
  fantasy: {
    fog: ["/map-tiles/Fantasy/Sala_degli_Specchi_01.png"],
    room: ["/map-tiles/Fantasy/Camera_da_letto_01.png", "/map-tiles/Fantasy/Sala_pranzo_01.png"],
    archive: ["/map-tiles/Fantasy/Biblioteca_01.png", "/map-tiles/Fantasy/Sala_delle_mappe_01.png"],
    lab: ["/map-tiles/Fantasy/Laboratorio_Alchemico_01.png", "/map-tiles/Fantasy/Stanza _del_mago_01.png"],
    ritual: ["/map-tiles/Fantasy/Tempio_01.png", "/map-tiles/Fantasy/Cripta_01.png"],
    outdoor: ["/map-tiles/Fantasy/Giardino_01.png", "/map-tiles/Fantasy/Stalla_01.png"],
    storage: ["/map-tiles/Fantasy/Armeria_01.png", "/map-tiles/Fantasy/Tesoreria_01.png", "/map-tiles/Fantasy/Cantina_01.png"],
    fortified: ["/map-tiles/Fantasy/Sala_di_Guardia_01.png", "/map-tiles/Fantasy/Prigione_01.png"],
    connector: ["/map-tiles/Fantasy/Sala_degli_Specchi_01.png", "/map-tiles/Fantasy/Cantina_01.png"],
    cafeteria: ["/map-tiles/Fantasy/Cucina_01.png", "/map-tiles/Fantasy/Sala_pranzo_01.png", "/map-tiles/Fantasy/Taverna_01.png"],
    quarters: ["/map-tiles/Fantasy/Camera_da_letto_01.png"],
    control: ["/map-tiles/Fantasy/Sala_delle_mappe_01.png", "/map-tiles/Fantasy/Stanza _del_mago_01.png"],
    command_bridge: ["/map-tiles/Fantasy/Sala_del_trono_01.png", "/map-tiles/Fantasy/Sala_delle_mappe_01.png"],
    tech: ["/map-tiles/Fantasy/Officina_01.png", "/map-tiles/Fantasy/Laboratorio_Alchemico_01.png"],
    medical: ["/map-tiles/Fantasy/Tempio_01.png", "/map-tiles/Fantasy/Laboratorio_Alchemico_01.png"],
    hangar: ["/map-tiles/Fantasy/Stalla_01.png"],
    recreation: ["/map-tiles/Fantasy/Taverna_01.png", "/map-tiles/Fantasy/Sala_degli_Specchi_01.png"],
    training: ["/map-tiles/Fantasy/Sala_di_Guardia_01.png", "/map-tiles/Fantasy/Armeria_01.png"],
  },
};

const EXACT_NODE_ARCHETYPES = {
  "stazione di comunicazione": "communications",
  "stazione comunicazione": "communications",
  "camera ibernazione": "cryo",
  ibernazione: "cryo",
  "ponte di comando": "command_bridge",
  "server centrale": "server",
  server: "server",
  infermeria: "medical",
  laboratorio: "lab",
  lab: "lab",
  archivio: "archive",
  mensa: "cafeteria",
  dormitori: "quarters",
  alloggi: "quarters",
  serra: "greenhouse",
  "corridoio tecnico": "technical_corridor",
  corridoio: "connector",
  connettore: "connector",
  deposito: "storage",
  magazzino: "storage",
  reattore: "reactor",
  controllo: "control",
  palestra: "training",
  "palestra tecnologica": "training",
  "stanza fortificata": "fortified",
  "stanza divertimento": "recreation",
  "stanza generica": "room",
  "sala del trono": "command_bridge",
  trono: "command_bridge",
  cripta: "ritual",
  tempio: "ritual",
  cappella: "ritual",
  altare: "ritual",
  armeria: "storage",
  tesoreria: "storage",
  cantina: "storage",
  prigione: "fortified",
  "sala di guardia": "fortified",
  taverna: "cafeteria",
  cucina: "cafeteria",
  giardino: "outdoor",
  stalla: "outdoor",
  "sala delle mappe": "archive",
  "laboratorio alchemico": "lab",
  officina: "tech",
  "camera da letto": "quarters",
  "stanza del mago": "lab",
};

const FANTASY_EXACT_TILE_OPTIONS = [
  {
    pattern: /sala delle mappe|mappe|cartograf/,
    tiles: ["/map-tiles/Fantasy/Sala_delle_mappe_01.png"],
  },
  {
    pattern: /biblioteca|libreria|scriptorium|archiv|registro|registri|genealog|pergamene?|codic[ei]|manoscritt/,
    tiles: ["/map-tiles/Fantasy/Biblioteca_01.png"],
  },
  {
    pattern: /cripta|sepolcr|tomba|tombe|sarcofag|catacomb|ossario|camera sepolcrale/,
    tiles: ["/map-tiles/Fantasy/Cripta_01.png"],
  },
  {
    pattern: /cappella|tempio|santuario|altare|ritual|sacrario|sigillo/,
    tiles: ["/map-tiles/Fantasy/Tempio_01.png"],
  },
  {
    pattern: /prigione|celle?|cella|penitenziale|segrete?|carcere|gabbia/,
    tiles: ["/map-tiles/Fantasy/Prigione_01.png"],
  },
  {
    pattern: /sala di guardia|posto di guardia|guardia|guardie|caserma/,
    tiles: ["/map-tiles/Fantasy/Sala_di_Guardia_01.png"],
  },
  {
    pattern: /sala del trono|trono|udienza|regnante|corona/,
    tiles: ["/map-tiles/Fantasy/Sala_del_trono_01.png"],
  },
  {
    pattern: /laboratorio alchemico|alchem|laboratorio|distill|ampolle?|elisir/,
    tiles: ["/map-tiles/Fantasy/Laboratorio_Alchemico_01.png"],
  },
  {
    pattern: /stanza del mago|mago|arcano|incantesim|grimorio/,
    tiles: ["/map-tiles/Fantasy/Stanza _del_mago_01.png"],
  },
  {
    pattern: /armeria|armi|armatura|arsenale/,
    tiles: ["/map-tiles/Fantasy/Armeria_01.png"],
  },
  {
    pattern: /tesoreria|tesoro|forziere|caveau|gioiell/,
    tiles: ["/map-tiles/Fantasy/Tesoreria_01.png"],
  },
  {
    pattern: /cantina|dispensa|scorte|barili?|botti/,
    tiles: ["/map-tiles/Fantasy/Cantina_01.png"],
  },
  {
    pattern: /cucina|forno|focolare/,
    tiles: ["/map-tiles/Fantasy/Cucina_01.png"],
  },
  {
    pattern: /sala pranzo|refettorio|banchetto|mensa/,
    tiles: ["/map-tiles/Fantasy/Sala_pranzo_01.png"],
  },
  {
    pattern: /taverna|locanda|osteria|birreria/,
    tiles: ["/map-tiles/Fantasy/Taverna_01.png"],
  },
  {
    pattern: /giardino|cortile|bosco|foresta|orto|parco/,
    tiles: ["/map-tiles/Fantasy/Giardino_01.png"],
  },
  {
    pattern: /stalla|scuderia|cavall|carrozze?/,
    tiles: ["/map-tiles/Fantasy/Stalla_01.png"],
  },
  {
    pattern: /officina|fucina|forgia|attrezzi|meccanism/,
    tiles: ["/map-tiles/Fantasy/Officina_01.png"],
  },
  {
    pattern: /camera da letto|camera|dormitorio|alloggi?|quartieri/,
    tiles: ["/map-tiles/Fantasy/Camera_da_letto_01.png"],
  },
  {
    pattern: /specchi|sala degli specchi|galleria/,
    tiles: ["/map-tiles/Fantasy/Sala_degli_Specchi_01.png"],
  },
];

function normalizeNodeText(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function nodeToTileArchetype(node, genre) {
  const exactKind = normalizeNodeText(node?.kind);
  const exactName = normalizeNodeText(node?.name);
  if (EXACT_NODE_ARCHETYPES[exactKind]) return EXACT_NODE_ARCHETYPES[exactKind];
  if (EXACT_NODE_ARCHETYPES[exactName]) return EXACT_NODE_ARCHETYPES[exactName];

  const text = normalizeNodeText(`${node?.name || ""} ${node?.kind || ""} ${(node?.tags || []).join(" ")}`);
  if (text.match(/stazione.*comunic|communication|comunicazioni?/)) return "communications";
  if (text.match(/ponte.*comando|command bridge|ponte|comando/)) return "command_bridge";
  if (text.match(/server|mainframe|datacenter|sala server/)) return "server";
  if (text.match(/ibernazione|cryo|cryogenic|stasi/)) return "cryo";
  if (text.match(/mensa|cafeteria|canteen|refettorio|cucina|sala pranzo|taverna|locanda|osteria/)) return "cafeteria";
  if (text.match(/dormitor|quarters|alloggi|cuccette|camera da letto/)) return "quarters";
  if (text.match(/divertiment|giochi|recreation|svago|lounge/)) return "recreation";
  if (text.match(/serra|greenhouse|idropon/)) return "greenhouse";
  if (text.match(/corridoio tecnico|technical corridor|manutenz|service corridor/)) return "technical_corridor";
  if (text.match(/palestra|training|gym|simulazione/)) return "training";
  if (text.match(/reatt|nucleo|energia|generatore/)) return "reactor";
  if (text.match(/computer|controllo/)) return "control";
  if (text.match(/medic|infermer|cura|osped|chirurg/)) return "medical";
  if (text.match(/hangar|garage|landing|atterraggio|eliporto/)) return "hangar";
  if (text.match(/laboratorio|lab|ricerca|speriment|alchem|mago|arcano/)) return "lab";
  if (text.match(/archiv|biblioteca|libreria|library|scriptorium|studio|document|ufficio|registri|genealog|pergamene?/)) return "archive";
  if (text.match(/corridoio|tunnel|scala|passaggio|trincea|sentiero|strada/)) return "connector";
  if (text.match(/deposito|magazzino|armeria|stiva|loot|tesoreria|cantina|dispensa/)) return "storage";
  if (text.match(/bunker|fortezza|torre|guardia|trincea|fortificat|prigione|celle?|cella|penitenziale/)) return "fortified";
  if (text.match(/cappella|tempio|cripta|ritual|altare|sepolcr|tomba|sarcofag|santuario/)) return "ritual";
  if (text.match(/giardino|foresta|bosco|parco|cortile|palude|veleni/)) return "outdoor";
  return "room";
}

function exactFantasyTileOptions(node) {
  const text = normalizeNodeText(`${node?.name || ""} ${node?.kind || ""} ${(node?.tags || []).join(" ")}`);
  return FANTASY_EXACT_TILE_OPTIONS.find((entry) => entry.pattern.test(text))?.tiles || [];
}

export function tileImageForNode(node, genre) {
  const theme = genre?.includes("sci") ? "sci_fi" : normalizeNodeText(genre || "");
  const archetype = nodeToTileArchetype(node, genre);
  const exactOptions = theme === "fantasy" ? exactFantasyTileOptions(node) : [];
  const primaryOptions = TILE_CATALOG[theme]?.[archetype] || [];
  const fallbackOptions = TILE_CATALOG[theme]?.room || [];
  const options = [...exactOptions, ...primaryOptions, ...fallbackOptions].filter(Boolean);
  return options[0] || "";
}

export function fogTileImage(genre) {
  const theme = genre?.includes("sci") ? "sci_fi" : normalizeNodeText(genre || "");
  return TILE_CATALOG[theme]?.fog?.[0] || "";
}
