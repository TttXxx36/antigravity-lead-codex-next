# D17 candidate ancestry integration
2026-11-27: D16 0425f17e921ca09571f74c409c4234c35876ca1c / Run 46006220435 4/4 success; exact checkout and cleanup/EPERM test logs verified. D17 process-exit helper and streaming test blob identical to D16. Preserve D17 scheduler and read-only cleanup preview: the earlier plain-denial test is superseded by existing D17 scheduler tests proving no removal on dirty/unmerged and clean/merged preview, while force/delete-branch are denied. No code change, no production permission expansion, no main merge. New integrated exact head requires CI; formal gates unchanged.


2026-11-27 refresh: integrate updated D16 `835999d29e106d56ea4b9ee8c35e64c22fcdce60`, carrying D15 `cd140bf583c0023d1d2be1970eb3eb248cabf120` and D14 ancestry. Preserve D17 scheduler and read-only cleanup preview. New D16 and D17 exact-head CI pending; no deletion/permission expansion/formal merge.
