"""Stage Markdown review copies for ALT-Database-db; never publish to this web repo."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

SECTIONS = ('fandom-db', 'wiki-db', 'alt-db')
RULES = {
    'fandom-db': ('character', 'characters', 'faction', 'species', 'biography', 'crew', 'protagonist', 'npc'),
    'alt-db': ('planet', 'star system', 'solar system', 'coordinate', 'orbit', 'hex district', 'transit', 'space station', 'navigation'),
    'wiki-db': ('encyclopedia', 'glossary', 'terminology', 'reference', 'definition', 'historical', 'timeline', 'lore bible'),
}

def slugify(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')[:90] or 'untitled'

def frontmatter(content):
    match = re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|\Z)', content, re.S)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', key.strip()):
                result[key.strip().lower()] = value.strip().strip('"\'')
    return result

def classify(filename, content, hint=''):
    meta = frontmatter(content)
    explicit = (meta.get('section') or meta.get('portal') or hint).strip().lower()
    if explicit:
        if explicit in SECTIONS:
            return explicit, 'explicit section', False
        return None, 'unsupported explicit section', True
    sample = (filename + ' ' + content[:25000]).lower()
    counts = {
        section: sum(bool(re.search(r'(?<![\w])' + re.escape(term) + r'(?![\w])', sample)) for term in words)
        for section, words in RULES.items()
    }
    high = max(counts.values())
    leaders = [section for section, score in counts.items() if score == high]
    if not high or len(leaders) != 1:
        return None, 'ambiguous classification; manual review required', True
    return leaders[0], f'keywords: {high}', False

def process(incoming, output):
    incoming, output = Path(incoming).resolve(), Path(output).resolve()
    if not incoming.is_dir():
        raise ValueError('Input directory does not exist')
    if incoming == output:
        raise ValueError('Output must differ from input')
    sources = sorted(p for p in incoming.rglob('*') if p.is_file() and p.suffix.lower() == '.md')
    manifest = {'target_repository': 'BareBones-Projects/ALT-Database-db',
                'status': 'review-required', 'files': []}
    copies, destinations = [], set()
    for source in sources:
        raw = source.read_bytes()
        if len(raw) > 1024 * 1024:
            raise ValueError(f'Markdown exceeds 1 MiB: {source.name}')
        content = raw.decode('utf-8-sig')
        metadata = frontmatter(content)
        section, reason, review = classify(source.stem, content)
        slug = slugify(metadata.get('slug') or source.stem)
        dest = f'{section}/{slug}.md' if section else None
        if dest:
            if dest in destinations:
                raise ValueError(f'Duplicate destination: {dest}')
            destinations.add(dest)
            copies.append((source, output / dest))
        manifest['files'].append({
            'source': str(source.relative_to(incoming)), 'destination': dest,
            'section': section, 'needs_review': review, 'reason': reason,
            'sha256': hashlib.sha256(raw).hexdigest()
        })
    output.mkdir(parents=True, exist_ok=True)
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return manifest

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    print(json.dumps(process(args.input, args.output), indent=2))

if __name__ == '__main__':
    main()
