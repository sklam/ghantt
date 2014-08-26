# Build a gantt chart off the issues
# Depends on github3.py <https://pypi.python.org/pypi/github3.py>

from __future__ import division, print_function
from getpass import getpass
from pprint import pprint
from datetime import datetime
import pickle
from collections import OrderedDict

from github3 import login
from bokeh import plotting
from bokeh.objects import HoverTool, ColumnDataSource

###################################
# User configurable settings

# Repo's owner/organization
GH_USER = "numba"

# Repo's name
GH_REPO = "numba"

# Login as
GH_LOGIN_USER = "sklam"


###################################

# Other globals
DATA_FILE = "{}.{}.dat".format(GH_USER, GH_REPO)
SECONDS_PER_DAY = 60 * 60 * 24

def parse_iso_datetime(strrep):
    if strrep:
        return datetime.strptime(strrep, "%Y-%m-%dT%H:%M:%SZ")


class Issue(object):

    def __init__(self, json):
        self.assignee = json['assignee']
        self.closed_at = parse_iso_datetime(json['closed_at'])
        self.created_at = parse_iso_datetime(json['created_at'])
        self.updated_at = parse_iso_datetime(json['updated_at'])
        self.number = json['number']
        if 'pull_request' in json:
            self.pull_request = json['pull_request']['html_url']
        else:
            self.pull_request = None
        self.title = json['title']
        self.state = json['state']

    def __repr__(self):
        return "<Issue {}>".format(self.number)

    @property
    def length(self):
        if self.closed_at:
            fromdt = self.closed_at
        else:
            fromdt = datetime.utcnow()

        delta = fromdt - self.created_at
        return (delta.days + delta.seconds/SECONDS_PER_DAY)

    @property
    def ago(self):
        delta = self.created_at - datetime.utcnow()
        return delta.days + delta.seconds/SECONDS_PER_DAY



def iter_gh_issues(since=None):
    print("GH login")
    gh = login(GH_LOGIN_USER,
               getpass("password for {} > ".format(GH_LOGIN_USER)))

    issues = gh.iter_repo_issues(GH_USER, GH_REPO, state='all',
                                 since=since)
    for raw_iss in issues:
        yield raw_iss.to_json()


def _generate():
    packed = []
    ct = 0
    for iss in iter_gh_issues():
        packed.append(iss)
        ct += 1
        print("#{}".format(ct))

    with open(DATA_FILE, "wb") as fout:
        pickle.dump(packed, fout)

REDS = [
    '#FF7940',
    '#FF4C00',
    '#BF5B30',
    '#A63100',
    '#993322',
]

def assign_color(iss):
    if iss.state == 'open':
        days = min(iss.length, 360)
        ratio = int(days/360 * len(REDS) - 1)
        return REDS[ratio]

    else:
        return '#60D4AE'


def graph():
    print("Graphing")
    with open(DATA_FILE, "rb") as fin:
        issues = [Issue(x) for x in pickle.load(fin)]

    plotting.output_file("{}.{}.html".format(GH_USER, GH_REPO),
                         title="ghantt.py")

    numbers = [iss.number for iss in issues]

    source = ColumnDataSource(
        data=dict(
            number = [iss.number for iss in issues],
            ago = [iss.ago + iss.length/2 for iss in issues],
            length = [iss.length for iss in issues],
            title = [iss.title for iss in issues],
            pull_request = [iss.pull_request for iss in issues],
            color = [assign_color(iss) for iss in issues],
            since = ["{} days".format(int(abs(iss.ago))) for iss in issues],
        ),
    )
    plotting.hold()
    plotting.rect("ago", "number", "length", 1, source=source,
                  color="color", title="{}/{}".format(GH_USER, GH_REPO),
                  y_range=(min(numbers), max(numbers)),
                  tools="resize,hover,previewsave,pan,wheel_zoom",
                  fill_alpha=0.8)

    text_props = {
        "source": source,
        "angle": 0,
        "color": "black",
        "text_align": "left",
        "text_baseline": "middle"
    }

    plotting.grid().grid_line_color = None

    hover = [t for t in plotting.curplot().tools if isinstance(t, HoverTool)][0]
    hover.tooltips = OrderedDict([
        ("number", "@number"),
        ("title", "@title"),
        ("since", "@since"),
        ("pull_request", "@pull_request"),
    ])

    plotting.show()


def fetch():
    print("Fetch...")
    try:
        with open(DATA_FILE, "rb") as fin:
            issues = [x for x in pickle.load(fin)]
    except IOError:
        issues = []

    if issues:
        since = max(iss['created_at'] for iss in issues)
        print("Download issues since {}".format(since))
    else:
        since = None
        print("Download issues")

    newer_issues = list(iter_gh_issues(since=since))

    if newer_issues:
        issues.extend(newer_issues)

        print("Write...")
        with open(DATA_FILE, "wb") as fout:
            pickle.dump(issues, fout)

    print("Done Fetch")


if __name__ == "__main__":
    fetch()
    graph()

