"""Freeze paired, source-backed discrimination controls before observing any answers."""

from datetime import datetime
import hashlib
import json
import random
import re

from .core import DEFAULT_HOME, ROOT
from .iteration import save
from .validation import cutoff_corpus


PAIRS = [
    {
        "source": "2002.12186", "cutoff": "2020-06-30", "target": "vigor",
        "terms": ["building", "identity", "Recall@K"],
        "overlap": "Build a cross-view benchmark using university building identities with satellite, synthetic drone and street views; train a shared identity-discriminative retrieval baseline and score building retrieval with Recall@K and AP.",
        "distinct": "Replace the one-to-one aligned retrieval assumption by arbitrary query locations and multiple covering aerial references; learn an offset from the retrieved tile center to the query location and evaluate localization beyond exact reference identity.",
        "difference": "Multiple geographically covering positives and within-reference offset regression versus building-identity retrieval.",
        "target_term": "offset",
    },
    {
        "source": "2008.11646", "cutoff": "2022-12-31", "target": "sample4geo",
        "terms": ["square-ring", "partition", "cross-entropy"],
        "overlap": "Partition cross-view feature maps into concentric square rings around the image center, pool each part, and optimize part-wise identity classification so local contextual information supports matching under rotations.",
        "distinct": "Use a shared off-the-shelf image encoder with symmetric contrastive training; initialize hard negatives using geographic neighbors where coordinates exist, then refresh negative batches using embedding-neighbor similarity. The contribution is the negative-selection schedule, not a feature partition.",
        "difference": "Dynamic hard-negative selection changes the training sampling distribution, not spatial ring representation.",
        "target_term": "Dynamic Similarity Sampling",
    },
    {
        "source": "1812.03506", "cutoff": "2022-12-31", "target": "lightglue",
        "terms": ["Covisibility clustering", "Local feature matching", "distillation"],
        "overlap": "Distill a single network to supply global descriptors and local features; retrieve candidate images, cluster references by co-observed 3D points, and perform local geometric localization within those places.",
        "distinct": "Build a learned sparse pairwise matcher that predicts token confidence and matchability to prune confidently unmatchable keypoints and stop transformer layers early on easy image pairs, adapting both width and depth at inference.",
        "difference": "Adaptive computation inside pairwise matching versus hierarchical place retrieval and covisibility clustering.",
        "target_term": "early",
    },
    {
        "source": "2305.15404", "cutoff": "2023-12-31", "target": "mast3r",
        "terms": ["classification", "DINOv2", "robust regression"],
        "overlap": "For dense pairwise matching, use frozen pretrained coarse features, classify coarse correspondences over anchors to handle multimodality, and refine them using a separately trained local feature branch and robust regression losses.",
        "distinct": "Jointly predict cross-view 3D pointmaps and discriminative dense local descriptors; use reciprocal descriptor matching together with the pointmap representation for precise matching, rather than only classifying and refining 2D correspondence coordinates.",
        "difference": "Joint 3D pointmap and local-descriptor representation versus dense 2D coarse-classification/refinement.",
        "target_term": "local",
    },
    {
        "source": "2201.09201", "cutoff": "2025-12-31", "target": "skyreg",
        "terms": ["SDM", "siamese", "neighbor-search"],
        "overlap": "Collect a dense real-UAV positioning dataset, train a siamese transformer retrieval baseline, exploit spatially neighboring matches in postprocessing, and introduce a continuous distance-sensitive SDM retrieval metric.",
        "distinct": "Predict a geographic coordinate for every visible query pixel by aligning feed-forward 3D pointmaps from drone and satellite views; supervise and evaluate dense pixel-wise georegistration instead of only retrieving a camera location.",
        "difference": "Dense per-pixel 3D georegistration and evaluation versus image-level location retrieval.",
        "target_term": "each query pixel",
    },
]


def excerpts(text, terms, radius=1000):
    intervals = [(0, 2500)]
    for term in terms:
        match = re.search(re.escape(term), text, re.I)
        if match:
            intervals.append((max(0, match.start() - radius), min(len(text), match.end() + radius)))
    output = []
    for start, end in intervals:
        output.append({"location": f"extracted text characters {start}:{end}; PDF page {text[:start].count(chr(12)) + 1}",
                       "quote": text[start:end]})
    return output


def build():
    literature = json.loads((ROOT / "pilot/literature.json").read_text())
    papers = {p["id"]: p for p in literature["papers"]}
    sources, cases, key = [], [], []
    rows = [json.loads(s) for s in (DEFAULT_HOME / "iteration-sources/requests.jsonl").read_text().splitlines()]
    for index, pair in enumerate(PAIRS, 1):
        source_id = "S" + str(index)
        path = DEFAULT_HOME / "iteration-sources" / (pair["source"] + "v1.txt")
        text = path.read_text()
        match = re.search(r"arXiv:" + re.escape(pair["source"]) + r"v1\s+\[[^]]+\]\s+(\d{1,2}\s+\w+\s+\d{4})", text)
        if not match:
            raise ValueError(f"Unverified source version/date: {path}")
        date = datetime.strptime(match[1], "%d %b %Y").date().isoformat()
        paper = {"id": source_id, "date": date, "examined_version_date": date}
        if not cutoff_corpus([paper], pair["cutoff"])["included"]:
            raise ValueError("Temporal document leakage")
        receipt = next(r for r in rows if r.get("text_path") == str(path))
        sources.append({**paper, "url": receipt["url"], "pdf_sha256": receipt["sha256"],
                        "text_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "full_text_path": str(path), "excerpts": excerpts(text, pair["terms"])})
        target = papers[pair["target"]]
        target_path = ROOT / target["verification"]["cache"]
        target_text = target_path.read_text()
        if target["date"] <= pair["cutoff"]:
            raise ValueError("Target contribution is not post-cutoff")
        for label in ["overlap", "distinct"]:
            case = {"source_id": source_id, "cutoff": pair["cutoff"], "idea": pair[label]}
            cases.append(case)
            key.append({
                **case, "expected": label,
                "ground_truth_scope": "Substantive mechanism relative to supplied source; not an exhaustive historical novelty label",
                "distinct_contribution": pair["difference"],
                "later_published_target": {"title": target["title"], "url": target["url"], "date": target["date"],
                                           "text_path": str(target_path), "sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
                                           "excerpts": excerpts(target_text, [pair["target_term"]], radius=600)},
            })
    order = list(range(len(cases)))
    random.Random(1701).shuffle(order)
    public, hidden = [], []
    for number, index in enumerate(order, 1):
        cid = f"C{number:02}"
        public.append({"id": cid, **cases[index]})
        hidden.append({"id": cid, **key[index]})
    packet = {
        "scope": "Compare each idea ONLY with its assigned source. Decide whether the substantive mechanism/contribution is already present or distinguishable. This is not a worldwide novelty claim.",
        "temporal_policy": "Sources are version-1 documents dated before each cutoff. Do not use knowledge of later papers. Model pretraining leakage cannot be ruled out.",
        "access_limit": "Only verbatim selected excerpts are supplied; full preserved texts are available to the independent ground-truth auditor, not to the tool-free evaluator.",
        "sources": sources, "cases": public,
    }
    key_value = {
        "minimum_recall_per_class": .8, "cases": hidden,
        "limitations": [
            "Five paired source families, ten controls; cases are correlated and not a population accuracy estimate.",
            "Distinct labels mean distinguishable from the assigned source, not absence of all historical prior art.",
            "Later published work is a grounded positive control, not proof its every component was historically unprecedented.",
            "Document version cutoffs are enforced; pretrained-model hindsight and author/idea recognition remain possible.",
            "Source-ID and reason checks are mechanical; independent audit is needed for semantic validity.",
        ],
    }
    save("benchmark-input.json", packet)
    save("benchmark-key.json", key_value)
    save("benchmark-freeze.json", {
        "input_sha256": hashlib.sha256((ROOT / "pilot/iteration/benchmark-input.json").read_bytes()).hexdigest(),
        "key_sha256": hashlib.sha256((ROOT / "pilot/iteration/benchmark-key.json").read_bytes()).hexdigest(),
        "labels_hidden_from_evaluator": True, "outcomes_seen": False,
    })
    return packet


if __name__ == "__main__":
    print(f"Frozen {len(build()['cases'])} source-backed comparison controls.")
