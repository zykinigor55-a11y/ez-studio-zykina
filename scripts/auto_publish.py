#!/usr/bin/env python3
"""Build the artwork catalogue and pull public GitHub changes from a CLI-only cron.
Requires Python >= 3.6, no packages or credentials. Install outside the web root.
The installed runner never executes or imports code from the downloaded repository.
"""
import argparse
import datetime
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

REPOSITORY = 'zykinigor55-a11y/ez-studio-zykina'
BASE_URL = 'https://zykina-art.ru'
CATEGORIES = {'plastic':'Пластика', 'abstract':'Абстракция', 'images':'Образы', 'stories':'Истории'}
CATEGORY_KEYS = {v.lower():k for k,v in CATEGORIES.items()}
TEXT_KEYS = {'название':'title','коллекция':'category','категория':'category','материал':'material','размер':'size','размеры':'size','цена':'price','описание':'description','главная':'main','главное фото':'main','публиковать':'published'}
IMAGE_TYPES = {'.png','.jpg','.jpeg','.webp'}
RUNNER_VERSION = '2026-11-12.1'


def natural(value):
    return [int(x) if x.isdigit() else x.casefold() for x in re.split(r'(\d+)',str(value))]


def script_json(value):
    return json.dumps(value,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')


def read_metadata(directory):
    result={}
    for name in ('работа.json','artwork.json'):
        path=directory/name
        if path.is_file():
            try:
                data=json.loads(path.read_text(encoding='utf-8-sig'))
                if not isinstance(data,dict):raise ValueError('metadata must be an object')
                result.update(data)
            except (ValueError,UnicodeError) as error:
                raise ValueError('Invalid metadata in {}: {}'.format(path,error))
    path=directory/'описание.txt'
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):continue
            if ':' not in line:continue
            key,value=line.split(':',1)
            key=key.strip().lower();key=TEXT_KEYS.get(key,key)
            result[key]=value.strip()
    return result


def collect_works(site):
    site=Path(site);base=site/'assets'/'картины';works=[]
    if not base.is_dir():raise ValueError('Artwork folder is missing: '+str(base))
    directories=sorted((d for d in base.iterdir() if d.is_dir() and not d.name.startswith('.')),key=lambda p:natural(p.name))
    for directory in directories:
        if directory.is_symlink():raise ValueError('Artwork symlinks are not supported')
        metadata=read_metadata(directory)
        if str(metadata.get('published','yes')).strip().lower() in ('нет','false','no','0'):continue
        files=sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_TYPES),key=lambda p:natural(p.name))
        if any(p.is_symlink() for p in files):raise ValueError('Image symlinks are not supported')
        if not files:continue  # Safe while a folder is being uploaded in several commits.
        main_name=metadata.get('main')
        if main_name:
            main=next((p for p in files if p.name==main_name),None)
            if main is None:raise ValueError('Main image not found in '+str(directory))
        else:
            main=next((p for p in files if re.match(r'^(главн|глав|глан|main|cover)',p.stem,re.I)),files[0])
        files=[main]+[p for p in files if p!=main]
        folder=directory.name
        key=folder if re.match(r'^\d+$',folder) else hashlib.sha256(folder.encode('utf8')).hexdigest()[:12]
        title=str(metadata.get('title') or ('Работа '+folder if folder.isdigit() else folder)).strip()
        category=str(metadata.get('category','images')).strip().lower()
        category=CATEGORY_KEYS.get(category,category)
        if category not in CATEGORIES:raise ValueError('Unknown collection in '+str(directory))
        def image_url(p):return quote(p.relative_to(site/'assets').as_posix(),safe='/')
        thumb_name=metadata.get('thumbnail')
        thumb=(site/'assets'/thumb_name) if thumb_name else None
        if thumb is not None and ('..' in PurePosixPath(thumb_name).parts or not thumb.is_file()):raise ValueError('Invalid thumbnail')
        work={'id':'art-'+key,'title':title,'cat':category,'img':image_url(main),'thumb':quote(thumb_name,safe='/') if thumb_name else image_url(main),'photos':[image_url(p) for p in files], 'page':'kartiny/work-'+key+'/'}
        for field in ('description','material','size','price'):
            if metadata.get(field):work[field]=str(metadata[field])
        works.append(work)
    return works


PAGE_STYLE='''body{margin:0;background:#f4f0e9;color:#44352b;font:16px/1.65 Arial,sans-serif}main{max-width:1080px;margin:40px auto;padding:0 24px}a{color:inherit}h1{font:400 clamp(32px,6vw,58px)/1.12 Georgia,serif}nav{display:flex;flex-wrap:wrap;gap:20px}figure{margin:28px 0;text-align:center}figure img{max-width:100%;max-height:75vh;object-fit:contain}.details{display:flex;gap:16px;overflow-x:auto}.details img{max-width:240px;height:190px;object-fit:contain}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:28px}.grid img{width:100%;height:240px;object-fit:contain}.grid a{text-decoration:none}.grid img.clean-earth-edge{width:auto;max-width:100%;display:block;margin-inline:auto}.facts{display:grid;grid-template-columns:auto 1fr;gap:8px 24px;max-width:700px}dt{color:#84766b}dd{margin:0}.contact{display:inline-block;border:1px solid;padding:12px 20px;margin:20px 0}.clean-earth-edge{clip-path:inset(.75% 3.8% .75% 3.8%)}'''


def page_shell(title,description,path,body,structured=None):
    e=lambda value:html.escape(str(value),quote=True)
    schema='<script type="application/ld+json">'+script_json(structured)+'</script>' if structured else ''
    return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+' — Екатерина Зыкина</title><meta name="description" content="'+e(description)+'"><link rel="canonical" href="'+BASE_URL+'/'+path+'"><style>'+PAGE_STYLE+'</style>'+schema+'</head><body><main><nav><a href="/">Студия Екатерины Зыкиной</a><a href="/kartiny/">Все работы</a></nav>'+body+'</main></body></html>'


def build_site(site):
    site=Path(site);works=collect_works(site)
    index=site/'index.html';source=index.read_text(encoding='utf8')
    pattern=r'const works=\[.*?\];\s*(?=const catNames=)'
    if len(re.findall(pattern,source,re.S))!=1:raise ValueError('Catalogue marker is missing or ambiguous')
    output=re.sub(pattern,lambda m:'const works='+script_json(works)+';\n',source,flags=re.S)
    # Metadata is text, never trusted HTML inside the existing JS templates.
    if 'function safeArtworkText(' not in output:
        output=output.replace("const A='assets/';", "const A='assets/';\nfunction safeArtworkText(v){return String(v).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));}")
    output=output.replace('${w.title}','${safeArtworkText(w.title)}')
    if 'id="workPageLink"' not in output:
        output=output.replace('<div id="lightboxThumbs"','<a id="workPageLink" style="color:inherit;text-decoration:underline;font-size:14px" href="kartiny/">Описание и характеристики</a><div id="lightboxThumbs"')
        output=output.replace("const photos=w.photos||[w.img];", "const photos=w.photos||[w.img];\n byId('workPageLink').href=w.page||'kartiny/';")
    if 'href="kartiny/" class="catalogue-link"' not in output:
        output=output.replace('<a href="privacy.html">','<a href="kartiny/" class="catalogue-link">Каталог работ</a><a href="privacy.html">')
    e=lambda value:html.escape(str(value),quote=True)
    pages={};cards=[]
    for work in works:
        desc=work.get('description') or (work['title']+' — авторская работа Екатерины Зыкиной. Фотографии и детали произведения, индивидуальный заказ в студии.')
        facts=''.join('<dt>'+label+'</dt><dd>'+e(work[key])+'</dd>' for key,label in [('material','Материал'),('size','Размер'),('price','Стоимость')] if work.get(key))
        img='/assets/'+work['img'];thumb='/assets/'+work['thumb']
        photo_class=' class="clean-earth-edge"' if work['id']=='art-2' else ''
        body='<p>'+e(CATEGORIES[work['cat']])+'</p><h1>'+e(work['title'])+'</h1><figure><img'+photo_class+' src="'+img+'" alt="'+e(work['title'])+' — общий вид"></figure><p>'+e(desc)+'</p>'
        if facts:body+='<dl class="facts">'+facts+'</dl>'
        if len(work['photos'])>1:body+='<div class="details">'+''.join('<a href="/assets/'+photo+'"><img src="/assets/'+photo+'" loading="lazy" alt="'+e(work['title'])+' — деталь '+str(i)+'"></a>' for i,photo in enumerate(work['photos'][1:],1))+'</div>'
        body+='<a class="contact" href="/#order">Обсудить покупку или заказ</a>'
        structured={'@context':'https://schema.org','@type':'VisualArtwork','name':work['title'],'image':[BASE_URL+'/assets/'+p for p in work['photos']],'url':BASE_URL+'/'+work['page'],'description':desc,'creator':{'@type':'Person','name':'Екатерина Зыкина'}}
        if work.get('material'):structured['artMedium']=work['material']
        pages[work['page']+'index.html']=page_shell(work['title'],desc,work['page'],body,structured)
        cards.append('<article><a href="/'+work['page']+'"><img'+photo_class+' src="'+thumb+'" loading="lazy" alt="'+e(work['title'])+'"><h2>'+e(work['title'])+'</h2></a><p>'+e(CATEGORIES[work['cat']])+'</p></article>')
    pages['kartiny/index.html']=page_shell('Каталог авторских работ','Картины и интерьерные панно студии Екатерины Зыкиной.','kartiny/','<h1>Авторские работы</h1><div class="grid">'+''.join(cards)+'</div>')
    urls=[BASE_URL+'/',BASE_URL+'/kartiny/']+[BASE_URL+'/'+w['page'] for w in works]
    pages['sitemap.xml']='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+e(url)+'</loc></url>' for url in urls)+'</urlset>\n'
    # Everything is validated before replacing any build output.
    for rel,content in pages.items():
        p=site/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf8')
    old_pages=site/'assets'/'catalog'/'generated-pages.json'
    if old_pages.is_file():
        for rel in json.loads(old_pages.read_text(encoding='utf8')):
            if rel not in pages and re.match(r'^kartiny/work-[a-z0-9-]+/index\.html$',rel):
                path=site/rel
                if path.is_file():path.unlink()
    catalog=site/'assets'/'catalog';catalog.mkdir(parents=True,exist_ok=True)
    (catalog/'manifest.json').write_text(json.dumps(works,ensure_ascii=False,indent=2),encoding='utf8')
    old_pages.write_text(json.dumps(sorted(pages)),encoding='utf8')
    index.write_text(output,encoding='utf8')
    return works


def extract_public(archive,stage):
    stage=Path(stage);total=0;found=False
    with zipfile.ZipFile(str(archive)) as zipped:
        roots={PurePosixPath(i.filename).parts[0] for i in zipped.infolist() if i.filename}
        if len(roots)!=1:raise ValueError('Unexpected archive structure')
        for info in zipped.infolist():
            parts=PurePosixPath(info.filename).parts
            if info.filename.startswith('/') or '\\' in info.filename or '..' in parts:raise ValueError('Unsafe archive path')
            if stat.S_ISLNK(info.external_attr >> 16):raise ValueError('Archive symlink rejected')
            total+=info.file_size
            if total>2*1024**3:raise ValueError('Archive exceeds storage limit')
            if len(parts)<3 or parts[1]!='public' or info.is_dir():continue
            rel=Path(*parts[2:]);dest=stage/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            with zipped.open(info) as src,dest.open('wb') as dst:shutil.copyfileobj(src,dst)
            found=True
    if not found or not (stage/'index.html').is_file():raise ValueError('Public website is missing')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.digest()


def atomic_copy(src,dst):
    dst=Path(dst);dst.parent.mkdir(parents=True,exist_ok=True)
    temp=dst.with_name('.'+dst.name+'.ez-new')
    try:
        shutil.copyfile(str(src),str(temp));os.chmod(str(temp),0o644);os.replace(str(temp),str(dst))
    finally:
        if temp.exists():temp.unlink()


def confined_path(root,rel):
    parts=PurePosixPath(rel).parts
    if not parts or PurePosixPath(rel).is_absolute() or '..' in parts or '\\' in rel:
        raise ValueError('Unsafe live path')
    path=Path(root)
    for part in parts:
        path=path/part
        if path.is_symlink():raise ValueError('Symlink in live destination: '+rel)
    return path


def publish_site(stage,target,backup):
    stage=Path(stage);target=Path(target);backup=Path(backup)
    target.mkdir(parents=True,exist_ok=True);backup.mkdir(parents=True,exist_ok=True)
    if target.stat().st_dev!=backup.stat().st_dev:raise ValueError('Recovery directory must be on the same filesystem')
    files=sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
    if 'index.html' not in files:raise ValueError('Cannot publish without index')
    state=confined_path(target,'assets/catalog/deployed-files.json')
    previous=json.loads(state.read_text(encoding='utf8')) if state.is_file() else []
    # Validate persisted paths too; never remove a file outside this website.
    if any(PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts for p in previous):raise ValueError('Invalid deployed file list')
    stale=sorted(set(previous)-set(files));changed=[];created=[];saved=[]
    for rel in files+stale:confined_path(target,rel)
    for rel in files:
        dst=target/rel
        if dst.is_symlink():raise ValueError('Live file symlink rejected: '+rel)
        if dst.is_file() and digest(stage/rel)==digest(dst):continue
        changed.append(rel)
    for rel in changed+stale:
        old=target/rel
        if old.is_file():
            saved.append(rel);b=backup/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(str(old),str(b))
        elif rel in changed:created.append(rel)
    try:
        # Media and supporting pages first; gallery index switches only after all copies succeed.
        for rel in sorted(changed,key=lambda p:p=='index.html'):atomic_copy(stage/rel,target/rel)
        for rel in stale:
            path=target/rel
            if path.is_file():path.unlink()
        state.parent.mkdir(parents=True,exist_ok=True)
        temp=state.with_suffix('.new');temp.write_text(json.dumps(files),encoding='utf8');os.replace(str(temp),str(state))
    except Exception:
        for rel in created:
            dst=target/rel
            if dst.is_file():dst.unlink()
        for rel in saved:
            dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            os.replace(str(backup/rel),str(dst))
        raise
    return len(changed)


def fetch_head():
    request=Request('https://api.github.com/repos/'+REPOSITORY+'/git/ref/heads/main',headers={'User-Agent':'EZ-Studio-Publisher/1.0','Accept':'application/vnd.github+json'})
    with urlopen(request,timeout=30) as response:data=json.loads(response.read(2*1024*1024).decode('utf8'))
    sha=data['object']['sha']
    if not re.match(r'^[a-f0-9]{40}$',sha):raise ValueError('Invalid commit SHA')
    return sha


def download_revision(sha,path):
    req=Request('https://github.com/'+REPOSITORY+'/archive/'+sha+'.zip',headers={'User-Agent':'EZ-Studio-Publisher/1.0'})
    total=0
    with urlopen(req,timeout=180) as source,Path(path).open('wb') as dest:
        while True:
            chunk=source.read(1024*1024)
            if not chunk:break
            total+=len(chunk)
            if total>1024**3:raise ValueError('Download exceeds limit')
            dest.write(chunk)


def sync(site,state_dir):
    site=Path(site).resolve();state_dir=Path(state_dir).resolve();state_dir.mkdir(parents=True,exist_ok=True)
    if state_dir==site or site in state_dir.parents:raise ValueError('Publisher state must be outside the public site')
    with (state_dir/'update.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'status':'busy'}
        revision=fetch_head();last=state_dir/'last-success.json'
        if last.is_file() and json.loads(last.read_text(encoding='utf8')).get('commit')==revision:return {'status':'unchanged','commit':revision}
        with tempfile.TemporaryDirectory(prefix='build-',dir=str(state_dir)) as temp:
            temp=Path(temp);archive=temp/'repo.zip';stage=temp/'public'
            download_revision(revision,archive);extract_public(archive,stage);works=build_site(stage)
            status={'status':'published','commit':revision,'works':len(works),'updated_at':datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z','runner_version':RUNNER_VERSION}
            (stage/'assets/catalog/deployment.json').write_text(json.dumps(status),encoding='utf8')
            changed=publish_site(stage,site,temp/'backup')
            # Retain the previous files outside the public directory for recovery.
            previous=state_dir/'previous-files'
            if previous.exists():shutil.rmtree(str(previous))
            shutil.copytree(str(temp/'backup'),str(previous))
            last.write_text(json.dumps(status,indent=2),encoding='utf8')
            status['changed_files']=changed
            return status


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build');parser.add_argument('--site');parser.add_argument('--state');args=parser.parse_args()
    if args.build:
        works=build_site(Path(args.build));print(json.dumps({'works':len(works),'status':'built'},ensure_ascii=False));return 0
    if not args.site or not args.state:parser.error('--site and --state are required for sync')
    try:print(json.dumps(sync(args.site,args.state),ensure_ascii=False));return 0
    except Exception as error:
        record={'status':'failed','time':datetime.datetime.utcnow().isoformat()+'Z','error':str(error)}
        state=Path(args.state)
        if state.is_dir():(state/'last-error.json').write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
        print(json.dumps(record,ensure_ascii=False),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
