"""
Rinomina tutti i file avventura con il pattern:
  pdf_<slug_titolo>.json   (se source_mode == pdf_import)
  ai_<slug_titolo>.json    (se source_mode == ai_generated)

Aggiorna anche il campo id interno al JSON.
Gestisce i conflitti di nome aggiungendo un suffisso numerico.
"""
import json, os, glob, re, shutil

BASE = os.path.join(os.path.dirname(__file__), '..', 'data', 'compiled_adventures')
BASE = os.path.normpath(BASE)

# Titoli brutti noti → override manuale
TITLE_OVERRIDES = {
    'adv_86219707bb': 'The Vast Vermin Swamp',
    'adv_fb33db3a62': 'Steve Jackson Games Sampler',   # titolo spazzatura dal PDF
    'adv_edaa0beb0c': 'The Temple',                    # titolo incompleto dal PDF
    'adv_1d15157bf0': 'Index',                         # era "Indice" (pagina indice)
}

def slugify(title: str) -> str:
    """Trasforma il titolo in un slug file-system safe."""
    s = title.lower()
    # rimuovi apostrofi/accenti comuni
    s = s.replace("'", '').replace(''', '').replace(''', '')
    s = re.sub(r'[àáâã]', 'a', s)
    s = re.sub(r'[èéêë]', 'e', s)
    s = re.sub(r'[ìíîï]', 'i', s)
    s = re.sub(r'[òóôõ]', 'o', s)
    s = re.sub(r'[ùúûü]', 'u', s)
    # rimpiazza tutto ciò che non è alfanumerico con underscore
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    # tronca a max 50 char (word boundary)
    if len(s) > 50:
        s = s[:50].rsplit('_', 1)[0]
    return s


def build_new_name(old_id: str, title: str, source_mode: str) -> str:
    title_clean = TITLE_OVERRIDES.get(old_id, title)
    slug = slugify(title_clean)
    prefix = 'ai' if 'ai' in source_mode else 'pdf'
    return f'{prefix}_{slug}'


def unique_path(folder: str, stem: str) -> str:
    """Ritorna un path non in conflitto (aggiunge _2, _3 … se necessario)."""
    candidate = os.path.join(folder, stem + '.json')
    if not os.path.exists(candidate):
        return candidate
    i = 2
    while True:
        candidate = os.path.join(folder, f'{stem}_{i}.json')
        if not os.path.exists(candidate):
            return candidate
        i += 1


def process_folder(folder: str):
    files = sorted(glob.glob(os.path.join(folder, 'adv_*.json')))
    if not files:
        return
    genre = os.path.basename(folder)
    print(f'\n📂  {genre}/')
    for old_path in files:
        with open(old_path) as f:
            raw = json.load(f)
        key = 'adventure_definition' if 'adventure_definition' in raw else None
        d = raw[key] if key else raw

        old_id    = d.get('id', os.path.splitext(os.path.basename(old_path))[0])
        title     = d.get('title', old_id)
        source    = d.get('source_mode', d.get('source_type', 'pdf_import'))

        new_stem  = build_new_name(old_id, title, source)
        new_path  = unique_path(folder, new_stem)
        new_id    = os.path.splitext(os.path.basename(new_path))[0]

        # Aggiorna id nel JSON
        d['id'] = new_id
        if key:
            raw[key] = d
        else:
            raw = d

        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        os.remove(old_path)

        old_name = os.path.basename(old_path)
        new_name = os.path.basename(new_path)
        print(f'  {old_name:<30}  →  {new_name}')


if __name__ == '__main__':
    genres = [d for d in os.listdir(BASE)
              if os.path.isdir(os.path.join(BASE, d)) and not d.startswith('_')]
    for g in sorted(genres):
        process_folder(os.path.join(BASE, g))
    print('\n✅  Rinomina completata.')
