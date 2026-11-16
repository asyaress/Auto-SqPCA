# Manuscript-to-artifact map

The labels describe when the result was added. `EXPLORATORY_POST_HOC` checks do not revise the frozen method. Hashes below refer to the unmodified files named in the result column, in order. The manuscript captions were inspected in the revised MethodsX document supplied with the project; original output file numbering differs from manuscript numbering.

| Manuscript item | Script | Result file(s) | SHA-256 | Label |
|---|---|---|---|---|
| Table 1 / Fig. 1 workflow | Editorial composition<br> no archived one-command source | figures/manuscript/Fig1.png | 9d464e4cf4eded84a0f6d7221c9047939af38b2a9e71114bf844f8f4189f1446 | pre-specified |
| Table 2 centering identification | phase2a/G2R/g2r.py | results/phase2/G2R/G2R_holdout_metrics.csv | e7ce738382dc5606c9edaa37fb768b1368497ae80036686583641bc675e3e781 | pre-specified |
| Fig. 2 Frobenius / |r| PC1 (381 matrices) | phase2a/G4R/g4r_run.py (metrics)<br> exact plotting script UNRESOLVED | results/phase2/G4R/G3R_structure_metrics.csv | e676970aa70ce8fd83cf6ca7fca634357f0c62413a8ef47dee86a9b02205b45b | pre-specified |
| Tables 3–4 E1 gaps | phase3/f3_e1_eval.py<br> phase3/f3b_e1_secondary.py | results/phase3/F3_E1_holdout_summary.csv<br> results/phase3/F3_E1_secondary_metrics.csv | 471f5a273e8915ce25b4a3a828da0cce1a35d1c7758eabfdded26121ea7f4dca<br>6d752ddc1c5312e39ccea5d5eacac1f775b8cf9bc762ee25dec2e3fee41720ca | pre-specified |
| Fig. 3 E1 gap curves | phase3/f3_e1_eval.py | phase3/F3A_figure1_error_curves.png<br> results/phase3/F3_E1_holdout_summary.csv | 292f8cb00dd62de2a64978b27e64927c605c994f0b003d6e895c234ba208b1ad<br>471f5a273e8915ce25b4a3a828da0cce1a35d1c7758eabfdded26121ea7f4dca | pre-specified |
| Fig. 4 E1 target not detected | phase3/f3_e1_eval.py | phase3/F3A_figure2_TND.png<br> results/phase3/F3_E1_TND_summary.csv | 95133de50499336a6dc3158073b49803e06544e7945dbbda79eb03e53ce62847<br>f41482ddbbfc6356d3cbd21b8da54982a8047b51ff1b06b78397239cdc93b924 | pre-specified |
| Table 5 U2 operating range | phase3/audit_add/audit_static.py | results/post_hoc/U2_operating_range_ratios.csv | 4374b6fc84f1ca5a2ab62a54cca0567f3a76529373630534aa6839126016fc56 | EXPLORATORY_POST_HOC |
| Table 6 U3 full workflow | phase3/audit_add/audit_u3.py | results/post_hoc/U3_summary.csv<br> results/post_hoc/U3_full_pipeline_cases.csv | 7e71907caafc614068478fec9f6a0f075ef4c74433944320073c0f36a0da3417<br>7e0532152e4a4d30872d7ec2893d46530a3a464526a9a3f782d163b26a05592f | EXPLORATORY_POST_HOC |
| Table 7 U1 iteration cap | phase3/audit_add/audit_u1.py | results/post_hoc/U1_summary.csv<br> results/post_hoc/U1_E3_capped.csv | 00512f8915204e817d7c4058e62265c9a1aba74284504105e6ec5e8adc4d8189<br>7b60392cf217a19b232305769b5baaf19b5fcad97902aa413b34e70734193d1b | EXPLORATORY_POST_HOC |
| Fig. 5 E2 risk–coverage and text | phase3/f3b_figures.py | results/phase3/F3_E2_risk_coverage.csv<br> results/phase3/F3_E2_result.json<br> phase3/F3B_figure3_risk_coverage.png | 45e8152f8e32494b83cb356e23b7ae5a2f0ee42a25856d007b14397f0158e5b7<br>128c37e4e8886a27a7beb8b13ba9596ca26c79944f39ec75847fb48574e78240<br>6db4b57e6c3c2e691ae6564dba40dec037f5d3165d0a7fca8cf628418c0de228 | pre-specified |
| Fig. 5 band coverage U5 check | phase3/audit_add/audit_u5.py | results/post_hoc/U5_band_coverage.csv | 57e5cdb87f155ba5463f2252c8e37f8c35f885c1a755099d2277c031c51ebdc0 | EXPLORATORY_POST_HOC |
| Tables 8–9 E3 station summary | phase3/f3b_e3_summary.py | results/phase3/F3_E3_station_summary.csv<br> results/phase3/F3_E3_cases.csv | f02c2739cb4b8cd717fb2e3a89f6c9d851bdf953c8699a283142bd45ae5863d4<br>1777d73c47ea52b629e985b93db3906b7d4467cdf4a00248d88fe1853c81f84e | pre-specified |
| Tables 8–9 U4 RMSE | phase3/audit_add/audit_static.py | results/post_hoc/U4_rmse_by_station_component.csv | c82ee6d5c113a081493432dbbcfe957c24bc184d788161d49c424c2fbee1e572 | EXPLORATORY_POST_HOC |
| Fig. 6 E3 latitude | phase3/f3b_figures.py | results/phase3/F3_E3_cases.csv<br> phase3/F3B_figure4_E3_latitude.png | 1777d73c47ea52b629e985b93db3906b7d4467cdf4a00248d88fe1853c81f84e<br>63c6f1178ee15b5b54a24eef30955dc3ee569ecf82c1c747340ec5555d57f8d9 | pre-specified |
| Fig. 7 E3 example curves | phase3/f3b_figures.py | results/phase3/F3_E3_examples.json<br> phase3/F3B_figure5_examples.png | 85ad690fbf640013acfa0953d7b803e59311dfa0ceb22bc2de448a082ffb070d<br>6f6fe93bd78213640c6aa0a3e8d63b5276bad6e31ef34f5430da349bca3e5ed1 | pre-specified |
| Targeted checks of implementation | provenance/audit_tests/audit_tests.py | provenance/audit_tests/results_2026-11-15.json | 6e9ca1a5401ac24ebda48d2dee93c5a2857b1af490a4665cd43c4f5b3f61e0f6 | EXPLORATORY_POST_HOC |

Fig. 1 is an editorial workflow drawing; its final 600-dpi PNG is archived here, but the editable source is **UNRESOLVED**. Fig. 2 has authenticated source metrics but no archived exact plotting script. The archived E1 and E3 figure scripts are retained byte-for-byte. The wrapper regenerates five E1/E2/E3 analytical panels from checked CSV/JSON in temporary directories. Pixel arrays match the archived analytical PNGs; PNG byte hashes differ because metadata differs. The final manuscript panels are English-language editorial layouts and were visually checked against the analytical plots and point counts, not claimed pixel-identical to them.

## Final manuscript images

These seven images were extracted byte-for-byte from the supplied `Figures_600dpi.zip`; they are not substitutes for the analytical CSV/JSON above.

| Figure | Final PNG | SHA-256 |
|---|---|---|
| Fig. 1 | `figures/manuscript/Fig1.png` | `9d464e4cf4eded84a0f6d7221c9047939af38b2a9e71114bf844f8f4189f1446` |
| Fig. 2 | `figures/manuscript/Fig2.png` | `e15dcff899626ee75a1050d134afd8608ce2c339322248804655beb7cdfbdfda` |
| Fig. 3 | `figures/manuscript/Fig3.png` | `626128de3a06dbf07725397584d7af170527dc53fcb0df06d0b3ade56c8659ba` |
| Fig. 4 | `figures/manuscript/Fig4.png` | `e71cf2887014c9cdc2433a82bedb05334fce98c2b97f222c573bf7cc9142611e` |
| Fig. 5 | `figures/manuscript/Fig5.png` | `142afde74db8cac39f6c7afbb3fb90a3c85e981699f6be94d1fbabd79fc1476c` |
| Fig. 6 | `figures/manuscript/Fig6.png` | `db3c6f875039438bf7aebee2f32808ebc4e334f314b6f11209c9eaf3c820fa52` |
| Fig. 7 | `figures/manuscript/Fig7.png` | `8cb43d155b060e903e03839dafd392b9087b5b54b35bc0b694d0a50cd35a2182` |
