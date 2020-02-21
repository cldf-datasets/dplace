import shutil
import pathlib

from nexus import NexusReader
from csvw.dsv import reader
from newick import loads

from cldfbench import Dataset as BaseDataset

DPLACE_DATA = pathlib.Path(__file__).resolve().parent.parent.parent / 'dplace' / 'dplace-data'


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "dplacetrees"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def cmd_download(self, args):
        for row in reader(DPLACE_DATA / 'phylogenies' / 'index.csv', dicts=True):
            if not row['id'].startswith('glottolog_'):
                self.raw_dir.joinpath(row['id']).mkdir(exist_ok=True)
                for fname in [
                    'posterior.trees',
                    'source.bib',
                    'summary.trees',
                    'taxa.csv',
                ]:
                    src = DPLACE_DATA / 'phylogenies' / row['id'] / fname
                    if src.exists():
                        shutil.copy(str(src), str(self.raw_dir / row['id'] / fname))

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_table(
            'trees.csv',
            {"name": 'ID', "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id"},
            {"name": 'Name', "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#name"},
            {"name": "rooted", "datatype": "boolean"},
            "Newick",
            "Type",
            "dplace_ID",
            "source",
        )
        #
        # FIXME: need to store the original tree ID and add the source!
        #
        t = args.writer.cldf.add_table(
            'treelabels.csv',
            {"name": 'ID', "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id"},
            {"name": 'Name', "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#name"},
            {"name": "Language_ID", "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#languageReference"},
            {"name": "Tree_ID", "separator": " "},
        )
        t.add_foreign_key('Tree_ID', 'trees.csv', 'ID')
        gcs = set()
        treelabel_id = 0
        tree_id = 0
        for d in sorted(self.raw_dir.iterdir(), key=lambda p: p.stem):
            if d.is_dir():
                print(d.stem)
                labels = {
                    l['taxon']: l['glottocode'] for l in reader(d.joinpath('taxa.csv'), dicts=True)}
                tree_ids = []
                if d.joinpath('summary.trees').exists():
                    nx = NexusReader.from_file(d.joinpath('summary.trees'))
                    nx.trees.detranslate()
                    tree = nx.trees[0]
                    newick = loads(tree.newick_string, strip_comments=True)[0]
                    for n in newick.walk():
                        n.name = labels.get(n.name, n.name)
                    tree_id += 1
                    args.writer.objects['trees.csv'].append({
                        'ID': str(tree_id),
                        'Name': tree.name,
                        'rooted': tree.rooted,
                        'Newick': newick.newick,
                        "Type": 'summary',
                        "dplace_id": d.stem,
                    })
                    tree_ids.append(tree_id)
                if d.joinpath('posterior.trees').exists():
                    nx = NexusReader.from_file(d.joinpath('posterior.trees'))
                    nx.trees.detranslate()
                    for i, tree in enumerate(nx.trees, start=1):
                        newick = loads(tree.newick_string, strip_comments=True)[0]
                        for n in newick.walk():
                            n.name = labels.get(n.name, n.name)
                        tree_id += 1
                        args.writer.objects['trees.csv'].append({
                            'ID': str(tree_id),
                            'Name': tree.name,
                            'rooted': tree.rooted,
                            'Newick': newick.newick,
                            "Type": 'sample',
                            "dplace_id": d.stem,
                        })
                        tree_ids.append(tree_id)
                for name, gc in sorted(labels.items()):
                    if gc:
                        gcs.add(gc)
                        treelabel_id += 1
                        args.writer.objects['treelabels.csv'].append({
                            'ID': str(treelabel_id),
                            'Name': name,
                            'Language_ID': gc,
                            'Tree_ID': [str(i) for i in tree_ids],
                        })
        for gc in sorted(gcs):
            lang = args.glottolog.api.cached_languoids.get(gc)
            if not lang:
                args.log.warning('invalid glottocode: {0}'.format(gc))
            args.writer.objects['LanguageTable'].append({
                'ID': gc,
                'Name': lang.name if lang else None,
                'Latitude': lang.latitude if lang else None,
                'Longitude': lang.longitude if lang else None,
                'ISO639P3code': lang.iso if lang else None,
                'Glottocode': gc,
            })
