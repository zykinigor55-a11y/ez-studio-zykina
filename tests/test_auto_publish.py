import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
import re

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'auto_publish.py'

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'automatic catalogue builder is missing')
        spec=importlib.util.spec_from_file_location('publisher',str(SCRIPT))
        self.p=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.p)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.site=self.root/'public';self.site.mkdir()
        self.site.joinpath('index.html').write_text('<html><head></head><body><section class="collections" id="collections">KEEP 02</section><script>const works=[];\nconst catNames={};</script></body></html>',encoding='utf8')
    def artwork(self,name='19',metadata=None):
        d=self.site/'assets'/'картины'/name;d.mkdir(parents=True)
        for f in ['главная.jpg','деталь 1.png','деталь 2.jpg']:(d/f).write_bytes(b'test image fixture')
        if metadata is not None:(d/'описание.txt').write_text(metadata,encoding='utf8')
        return d
    def test_new_folder_builds_gallery_page_and_sitemap_without_changing_02(self):
        self.artwork(metadata='Название: Белая волна\nКоллекция: Пластика\nМатериал: Гипс\nРазмер: 80 × 100 см\n')
        works=self.p.build_site(self.site)
        self.assertEqual(works[0]['title'],'Белая волна');self.assertEqual(works[0]['cat'],'plastic')
        self.assertEqual(len(works[0]['photos']),3)
        self.assertIn('KEEP 02',self.site.joinpath('index.html').read_text())
        page=self.site.joinpath('kartiny/work-19/index.html').read_text()
        self.assertIn('Белая волна',page);self.assertIn('Гипс',page);self.assertIn('80 × 100 см',page)
        self.assertIn('https://zykina-art.ru/kartiny/work-19/',self.site.joinpath('sitemap.xml').read_text())
    def test_fallback_without_metadata_is_usable(self):
        self.artwork();w=self.p.build_site(self.site)[0]
        self.assertEqual(w['title'],'Работа 19');self.assertEqual(w['cat'],'images')
    def test_metadata_preserves_existing_cover_and_title(self):
        d=self.artwork('6');(d/'работа.json').write_text(json.dumps({'title':'Слон','category':'images','main':'деталь 2.jpg'}),encoding='utf8')
        w=self.p.build_site(self.site)[0]
        self.assertEqual(w['photos'][0],__import__('urllib.parse',fromlist=['quote']).quote('картины/6/деталь 2.jpg',safe='/'));self.assertEqual(w['title'],'Слон')
    def test_broken_metadata_fails_before_rewriting_index(self):
        d=self.artwork();(d/'работа.json').write_text('{broken',encoding='utf8');before=(self.site/'index.html').read_bytes()
        with self.assertRaises(ValueError):self.p.build_site(self.site)
        self.assertEqual((self.site/'index.html').read_bytes(),before)
    def test_script_like_title_is_escaped_in_html_and_javascript(self):
        self.artwork(metadata='Название: </script><img src=x onerror=alert(1)>\n')
        self.p.build_site(self.site)
        page=(self.site/'kartiny/work-19/index.html').read_text();index=(self.site/'index.html').read_text()
        self.assertNotIn('<img src=x onerror',page);self.assertNotIn('</script><img src=x',index)
    def test_incomplete_new_upload_is_skipped_and_draft_is_hidden(self):
        self.artwork('19');d=self.site/'assets'/'картины'/'20';d.mkdir();(d/'описание.txt').write_text('Название: Скоро',encoding='utf8')
        d=self.artwork('21');(d/'описание.txt').write_text('Публиковать: нет',encoding='utf8')
        self.assertEqual(len(self.p.build_site(self.site)),1)
    def test_live_symlink_ancestor_cannot_write_outside_site(self):
        target=self.root/'live';target.mkdir();outside=self.root/'outside';outside.mkdir()
        (target/'assets').symlink_to(outside,target_is_directory=True)
        self.artwork();self.p.build_site(self.site)
        with self.assertRaises(ValueError):self.p.publish_site(self.site,target,self.root/'backup')
        self.assertEqual(list(outside.iterdir()),[])
    def test_live_symlink_ancestor_cannot_remove_outside_file(self):
        target=self.root/'live';target.mkdir();outside=self.root/'outside';outside.mkdir()
        (outside/'old.txt').write_text('keep',encoding='utf8');(target/'old').symlink_to(outside,target_is_directory=True)
        state=target/'assets/catalog';state.mkdir(parents=True)
        (state/'deployed-files.json').write_text(json.dumps(['old/old.txt']),encoding='utf8')
        self.artwork();self.p.build_site(self.site)
        with self.assertRaises(ValueError):self.p.publish_site(self.site,target,self.root/'backup')
        self.assertEqual((outside/'old.txt').read_text(),'keep')
    def test_untrusted_zip_cannot_escape_staging(self):
        zpath=self.root/'unsafe.zip'
        with zipfile.ZipFile(str(zpath),'w') as z:z.writestr('repo/../../escape.txt','bad')
        with self.assertRaises(ValueError):self.p.extract_public(zpath,self.root/'stage')
        self.assertFalse((self.root/'escape.txt').exists())
    def test_publication_retains_previous_site_after_copy_error(self):
        target=self.root/'live';target.mkdir();(target/'index.html').write_text('OLD',encoding='utf8')
        self.artwork();self.p.build_site(self.site)
        original=self.p.atomic_copy
        def failing(src,dst):
            if Path(dst).name=='index.html':raise OSError('simulated disk full')
            return original(src,dst)
        self.p.atomic_copy=failing
        with self.assertRaises(OSError):self.p.publish_site(self.site,target,self.root/'backup')
        self.assertEqual((target/'index.html').read_text(),'OLD')
    def test_disk_full_rollback_frees_new_files_and_restores_without_recopies(self):
        target=self.root/'live';target.mkdir();(target/'index.html').write_text('OLD INDEX',encoding='utf8')
        (target/'a-existing.txt').write_text('OLD LONG CONTENT',encoding='utf8')
        self.artwork();self.p.build_site(self.site)
        (self.site/'a-existing.txt').write_text('NEW',encoding='utf8');(self.site/'b-new.txt').write_text('occupies space',encoding='utf8')
        original_atomic=self.p.atomic_copy;original_copy=self.p.shutil.copy2;backup=self.root/'backup'
        def failing(src,dst):
            if Path(dst).name=='index.html':raise OSError('disk full')
            return original_atomic(src,dst)
        def no_recopy_when_full(src,dst,*a,**kw):
            if backup in Path(src).parents and (target/'b-new.txt').exists():raise OSError('not enough space for restore copy')
            return original_copy(src,dst,*a,**kw)
        self.p.atomic_copy=failing;self.p.shutil.copy2=no_recopy_when_full
        try:
            with self.assertRaises(OSError):self.p.publish_site(self.site,target,backup)
        finally:self.p.shutil.copy2=original_copy
        self.assertEqual((target/'a-existing.txt').read_text(),'OLD LONG CONTENT')
        self.assertEqual((target/'index.html').read_text(),'OLD INDEX');self.assertFalse((target/'b-new.txt').exists())
    def test_deleted_work_page_is_removed_but_unmanaged_files_remain(self):
        target=self.root/'live';target.mkdir();(target/'owner.txt').write_text('keep',encoding='utf8')
        self.artwork();self.p.build_site(self.site);self.p.publish_site(self.site,target,self.root/'backup1')
        shutil.rmtree(str(self.site/'assets'/'картины'/'19'));self.p.build_site(self.site);self.p.publish_site(self.site,target,self.root/'backup2')
        self.assertFalse((target/'kartiny/work-19/index.html').exists());self.assertTrue((target/'owner.txt').exists())

if __name__=='__main__':unittest.main()
