"""Publish the bounded finalist source packet; never turn internal ideas into prior art."""

import json

from .archive import Archive, Reference
from .core import DEFAULT_HOME, Store
from .mechanism_campaign import SOURCES, campaign, newline_excerpt, persist


def main():
    specs = [
        ("bundle", "Bundle Adjustment - A Modern Synthesis", 2000, "Vision Algorithms",
         "Schur elimination, inverse-Hessian covariance and MAP priors are established estimation operations.",
         "Survey and mathematical identities; not evidence of tested drone-specific performance.",
         [(329, 378, "Section 3: MAP priors and covariance"),
          (1309, 1412, "Section 6.1, equations 16-18: block inverse/Schur identity")]),
        ("degeneracy", "On Degeneracy of Optimization-based State Estimation Problems", 2016, "ICRA",
         "Eigenvalue-based degeneracy detection and retaining a prediction in weak directions.",
         "Camera/lidar ego-motion, not exact equivalence to every drone retrieval pipeline.",
         [(492, 518, "Section III.B: solution remapping"),
          (536, 553, "Section III.B: prediction versus solved directions")]),
        ("spectral", "Spectral GS-SLAM: Observability-Aware, Degeneracy-Robust Tracking for Real-Time 3D Gaussian Splatting SLAM",
         2026, "arXiv v2, 10 October 2026",
         "Hessian spectral degeneracy analysis and anisotropic prior information injection.",
         "Preprint; Gaussian ICP tracking, not a demonstration of M06's exact aerial pipeline.",
         [(418, 444, "Equation 8 and prior-information gating")]),
        ("metrology", "Metrological Characterization of a Laser-Camera 3D Vision System through Perspective-n-Point Pose Computation and Monte Carlo Simulations",
         2022, "ISPRS Archives",
         "Monte Carlo propagation of pose perturbations into projected-point error.",
         "Perturbs pose then projects points; does NOT establish DSM perturbation/PnP-RANSAC re-solving equivalence.",
         [(287, 312, "Section 2.3: sampled pose perturbations"),
          (350, 355, "Section 2.3: forward projection, not repeated PnP estimation")]),
    ]
    requests = [json.loads(line) for line in (SOURCES / "requests.jsonl").read_text().splitlines()]
    archive = Archive(DEFAULT_HOME / "archive")
    store = Store()
    papers = []
    for name, title, year, venue, mechanism, caveat, passages in specs:
        receipt = next(r for r in requests if r.get("path") == str(SOURCES / (name + ".pdf")))
        raw = Reference(**receipt["archive"])
        archive.read(raw)
        path = SOURCES / (name + ".txt")
        text = path.read_text()
        extracted = archive.store_text(text, raw=raw, extraction="pdftotext retained primary PDF")
        evidence = []
        for first, last, location in passages:
            start, quote = newline_excerpt(text, first, last)
            claim = archive.record_claim(claim=mechanism, source=raw, text=extracted,
                                         quote=quote, start=start, end=start + len(quote), location=location)
            archive.verify_manifest(claim)
            evidence.append({"claim": mechanism, "quote": quote, "location": location,
                             "url": receipt["url"], "archive_manifest": claim,
                             "verification": "Retained primary text; semantic comparison remains independently audited"})
        paper = {"id": "mf-" + name, "record_type": "external_publication", "title": title,
                 "year": year, "venue": venue, "url": receipt["url"], "source": receipt["url"],
                 "family": "Estimation theory and uncertainty", "mechanism": mechanism,
                 "contribution": mechanism, "limitations": [caveat],
                 "evaluation": "Only method passages examined for targeted prior art; no numerical performance claim imported",
                 "evidence": evidence, "access": "Preserved full PDF; targeted passages examined",
                 "verification": "Primary-source passages and identity examined; not an exhaustive paper reproduction"}
        store.put(campaign(), "papers", paper)
        papers.append(paper)
    persist("external-prior-art.json", papers)
    print(f"{len(papers)} primary references and {sum(len(p['evidence']) for p in papers)} exact passages published.")


if __name__ == "__main__":
    main()
