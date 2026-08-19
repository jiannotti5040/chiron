# Manifest errata

`MANIFEST.sha256` is a chain-hashed provenance artifact and is preserved
byte-identical; corrections to the tree it describes are recorded here
instead of edited into it.

**2026-07-04 — Windows-compatibility renames (content unchanged).**
Two source-material filenames contained literal `*` characters, which
Windows forbids in filenames — `actions/checkout` failed on every Windows
CI runner before any code could run. Renamed:

| Manifest path | New path | SHA-256 |
|---|---|---|
| `./source_materials/Files/*current*.pages` | `./source_materials/Files/current.pages` | unchanged |
| `./source_materials/RSLS_source_PDFs/*current*.pages` | `./source_materials/RSLS_source_PDFs/current.pages` | unchanged |

The file *contents* are byte-identical to what the manifest hashes; only
the names changed. Verify either file against its manifest line by hashing
the renamed file.

**2026-07-21 — Post-manifest addition: `uma/jacobian/` (new files, nothing renamed).**
Three files added after the manifest was sealed; the manifest itself is
preserved byte-identical, and these additions are recorded here per the
convention above:

| New path | What it is |
|---|---|
| `uma_build_v4/uma/jacobian/__init__.py` | exact-arithmetic verification of the 2026 Jacobian-conjecture counterexample (Alpöge 2026-07-20, Knill transcription): det J ≡ −2 as a polynomial identity + exact two-point collision, plus positive/discrimination controls |
| `uma_build_v4/uma/jacobian/__main__.py` | `python3 -m uma.jacobian` certificate CLI |
| `uma_build_v4/tests/test_jacobian.py` | 12 pytest gates (suite: 104 → 136 with the v4-ext files; all green 2026-07-21) |
| `uma_build_v4/docs/JACOBIAN_COUNTEREXAMPLE.md` | honest write-up: what is verified (arithmetic), what is not (provenance, n = 2, peer review) |

**2026-08-10 — Assistant signatures removed from six notes files (content
otherwise unchanged).**

Six files carried a trailing `*Signed: Claude (rebuild assistant)*` line and
first-person framing addressed to the repository owner. The signatures and
that framing were removed; the technical content — which parts of the rebuild
are reconstructions from the PDF corpus, which are additions, and which
questions the corpus could not settle — is unaltered. The manifest is
preserved byte-identical per the convention above, so the new digests are
recorded here:

| Path | SHA-256 (after) | Bytes |
|---|---|---|
| `./uma_build_v4/IMPASSES.md` | `f5008db8d528593da8e29ee9860843e0928341bb9630c71e9b872ac0a276e6f3` | 3587 |
| `./uma_build_v4/YOUR_NOTES.md` | `4886e2c716f0785eb183700c06a285c1bcac5fea1c0dade05a7b9b342f6ddf75` | 5839 |
| `./uma_build_v4/YOUR_CONTRIBUTIONS.md` | `9bcae3ea0024d8b5fb8475720526d92516d5f7917b2c5f835856c905ea3da466` | 3830 |
| `./baseline_v3/uma_build_v3/IMPASSES.md` | `5d255b5825ceda0674a7279a3a99870f403d92aae503a2d8df9caa91ff1af851` | 1678 |
| `./baseline_v3/uma_build_v3/YOUR_NOTES.md` | `4886e2c716f0785eb183700c06a285c1bcac5fea1c0dade05a7b9b342f6ddf75` | 5839 |
| `./baseline_v3/uma_build_v3/YOUR_CONTRIBUTIONS.md` | `9bcae3ea0024d8b5fb8475720526d92516d5f7917b2c5f835856c905ea3da466` | 3830 |

**Permanently unverifiable manifest entries.** Five manifest lines cover
`.pytest_cache` files, which pytest rewrites on every run. Those entries can
never verify and should be treated as out of scope for any integrity check
rather than as evidence of tampering.

**2026-08-10 — Divergences from the 2026-08 relicensing sweep, recorded in
arrears.**

The manifest was sealed before the repository relicensed from PolyForm
Noncommercial to Apache-2.0. That sweep rewrote licence headers across the
suite and was never recorded here, so a verifier reported most of the manifest
as failing — which reads as tampering and is not. The manifest remains
byte-identical; the current digests are recorded below, grouped by the commit
that produced them.


**`unknown` — ** (69 files)

| Path | SHA-256 (current) | Bytes |
|---|---|---|
| `./uma_build_v4/IMPASSES.md` | `f5008db8d528593da8e29ee9860843e0928341bb9630c71e9b872ac0a276e6f3` | 3587 |
| `./uma_build_v4/NEXT_SESSION.md` | `f2db692f9f98d46772611f80fd561f13ed2c8c1dbeea414cf180db1755cd6d63` | 11666 |
| `./uma_build_v4/README.md` | `4b07b9658aba828c1cae88afb80109e41744a37e4b7e57c31710ec7fca9c1b8a` | 12102 |
| `./uma_build_v4/YOUR_CONTRIBUTIONS.md` | `9bcae3ea0024d8b5fb8475720526d92516d5f7917b2c5f835856c905ea3da466` | 3830 |
| `./uma_build_v4/YOUR_NOTES.md` | `4886e2c716f0785eb183700c06a285c1bcac5fea1c0dade05a7b9b342f6ddf75` | 5839 |
| `./uma_build_v4/calibrate.py` | `86b75f665e255b101728e93e17ee79a3f4e4553c389c26d6f17410cc1b5eccf3` | 5093 |
| `./uma_build_v4/examples/rsls_frame_dragging.py` | `a3fc12ccaa94e7538331d5e18a07e07e72ef12c04216259cd2f95824be3f7664` | 3939 |
| `./uma_build_v4/examples/rsls_menger_substrate.py` | `2e1ea7dd9b9dc1834cab403ad2c083647c538d9d61e3adc9cecab665aae56d29` | 8957 |
| `./uma_build_v4/examples/rsls_phase_a.py` | `1b6ad1b4cc3c2309b4d87ebdb23008eb04f6321235c35ea61c27fcd98b293b72` | 7652 |
| `./uma_build_v4/examples/rsls_srb_lyapunov.py` | `b1a0240b6b58776dd71541092de131f67949d58a939734f84912c0741c961649` | 5032 |
| `./uma_build_v4/examples/rsls_stage3_perturbation.py` | `184872263fea451a40c14f2b8ce3a2221bc6bb1a4fa25a60521264707b0ed7da` | 5858 |
| `./uma_build_v4/examples/rsls_stage6_self_consistent.py` | `477bc86f16555e94df6c7f7fe9d08d231397b3771fadb290728700055e454681` | 4496 |
| `./uma_build_v4/examples/rsls_uma_integrated.py` | `eae8542e2727bc824e5131cc52a6e3672f30b8deabdfd5edd539f60043b7ee79` | 7449 |
| `./uma_build_v4/examples/run_pipeline.py` | `6a0b51f2e8b8e56a2b3ff9e8d5f46fc071932b4bcc5618b5cd2cafee5ffc937c` | 1107 |
| `./uma_build_v4/examples/sphere_uma_execution.py` | `8482d0bbbc6cea4d2ad78853db93906b4a430e76a97f0b59bbf99def1e1601bd` | 2089 |
| `./uma_build_v4/tests/test_frame_dragging.py` | `36d5c0e93d332a0e4b07a5380fca9a5a5e2abc2c998f6f346b5618a42616ba5f` | 6968 |
| `./uma_build_v4/tests/test_ligo_lisa.py` | `345fd23175172358567545d83b19bfa26f96f0daa2ea5babe8542469454ad4e6` | 3298 |
| `./uma_build_v4/tests/test_menger.py` | `0ce9c569bf6ab345e0275c56a24373e33df86eb532cfc3a29404e4423fbc225e` | 8258 |
| `./uma_build_v4/tests/test_rsls.py` | `2940054587b0897bbfcfea140ede1b60e8342cbb11693169834b8216156472f8` | 9634 |
| `./uma_build_v4/tests/test_sanity.py` | `e5e93d7419f6eb5bbe737237c3aa63011027e69cb439840de0789fced12d4dd6` | 7432 |
| `./uma_build_v4/tests/test_semantic.py` | `274fd71df946c111b47630acd0c85cf33d2027ea3ccc2e03462a8eb5934fac0b` | 7722 |
| `./uma_build_v4/tests/test_srb.py` | `5d9ebf0764d71771ab416485c7e2d74522f91bc2b798f76ceaf70207514efa82` | 4884 |
| `./uma_build_v4/tests/test_stage3.py` | `59e03088c853d993c9c1f4a035892dac0b3dcb4e6b39e99a2a399261a078f185` | 4369 |
| `./uma_build_v4/tests/test_stage6.py` | `92f76aa8a8c557f1e746df7ac111f308a8b132075aeb59d8561f8f2cc89aee8c` | 8974 |
| `./uma_build_v4/uma/__init__.py` | `d256f4ba5097e7f3e33566f65f1be605488b5c536b1c8995c4d499d12c97c1a6` | 836 |
| `./uma_build_v4/uma/client.py` | `af4e70570e3630ebeab7f24c6c46a8746969cbeacea696064467aef9da0f63be` | 5053 |
| `./uma_build_v4/uma/config.py` | `4580d4ae849940a80589af272884702658b4127725f3ab32140ba8d70f77bb5f` | 1733 |
| `./uma_build_v4/uma/core/__init__.py` | `f9ea6fa719e9332031f115b17ed11976084797d23cc9575dc353f736d325d65a` | 318 |
| `./uma_build_v4/uma/core/filter.py` | `8736bf96d698c9eb1639810b83523af65a74f5ddeb75525698989be01158f7c0` | 1810 |
| `./uma_build_v4/uma/core/projection.py` | `03d178186a2793432ed298a08ae278318dd6473a6f37b06b088aa103825e7241` | 2374 |
| `./uma_build_v4/uma/core/state.py` | `d92800f4013c1b8daf8cf6ac20b15ea79055332174dcfa79178ffb13ca13ab21` | 1520 |
| `./uma_build_v4/uma/dynamics/__init__.py` | `ffe25691fde202f8435a2a7046eb6ecb6fa037bfd4403ef602366923769d1545` | 272 |
| `./uma_build_v4/uma/dynamics/generic.py` | `53361c04830e77f61c4f34c1e45b05dd5a3fdd423670e3d5ea9f0fcc20bf34f5` | 4363 |
| `./uma_build_v4/uma/msr/__init__.py` | `aab4fd408fb2f9935efb83a1ae46820261f4195769fd3a920c295c1989ee8cf1` | 1040 |
| `./uma_build_v4/uma/msr/gr_fixed_point.py` | `28e0f696e3e6f2d64d0f0840f1975351c97821c2a361c2ebd540d914ab2221e3` | 3788 |
| `./uma_build_v4/uma/msr/metric_solver.py` | `45f8fab5579d714f4e423855680eef8a144f937509bdcbe9601963a31d3c1079` | 5302 |
| `./uma_build_v4/uma/msr/nonlinear_gr.py` | `e461536723549052aaf6d6073115539e4d0b0b2e02da502d75d6d50c02ab169e` | 7210 |
| `./uma_build_v4/uma/msr/stress_energy.py` | `5a9f618bf51465382bedf8461ba1a585a95c2c4fa59fdb86b18336d421b7e458` | 3647 |
| `./uma_build_v4/uma/msr/tensor_bridge.py` | `e970ee0382d8e3286e43d664f807a82b446c396131609c4341f6770283194d9b` | 8802 |
| `./uma_build_v4/uma/msr/wetterich_flow.py` | `1a8b86a83508c7ec6bfb54eba5b8f4c85c7cdafe2bbd4b334830237e182af5a1` | 1597 |
| `./uma_build_v4/uma/observations/__init__.py` | `eb69b71ce64790526795f39feed336731e3c1d5355c25844442938a2950f5d7b` | 236 |
| `./uma_build_v4/uma/observations/base.py` | `23f9569e8619fd9549836b9d7562c224777a0e41772ec3bceb0ea76b4779870d` | 1072 |
| `./uma_build_v4/uma/pipeline.py` | `7888aa23059682fac003a5553e55ca8a6c3b6c6adec6fcab65652f8f6576981c` | 16329 |
| `./uma_build_v4/uma/rsls/__init__.py` | `064fdcce02aea2cd4f7ce09174582d072d1091e0b750f75ae6aa94d945df65c3` | 4521 |
| `./uma_build_v4/uma/rsls/cattaneo.py` | `c4bc468e0407aed5bb191498f5faed005dfee848cd9bd009c42518eb8fd5b1d7` | 4038 |
| `./uma_build_v4/uma/rsls/coupling.py` | `9d9c3449fb1deabe3b6b7b76acfbe461e03d1d54efd47b8e430d89ba2a791d27` | 7005 |
| `./uma_build_v4/uma/rsls/frame_dragging.py` | `f09e683d1b6d5ad953acb098703c7c9485803a2902e2a150c31d3dd9a0e873a2` | 25906 |
| `./uma_build_v4/uma/rsls/hll.py` | `18125e6af9945529046751668f501906a7956bcc4f455514dbf063eb8de05b62` | 8410 |
| `./uma_build_v4/uma/rsls/ligo_lisa.py` | `6aa4a1b50fb91b21b9a08b2225af317141ffa2fe005c9bee83fd7a0f5bceb155` | 12416 |
| `./uma_build_v4/uma/rsls/memory.py` | `7b96720b3a02df56bce2b870523836c557c2c82ecc03ce0e93f46494c76cb3f7` | 10791 |
| `./uma_build_v4/uma/rsls/menger.py` | `e540eb871bd0930aef5779c4641a91750b97a97278468a7437b6c7196b359c46` | 13669 |
| `./uma_build_v4/uma/rsls/phase_a.py` | `5b97bda63c6bea4a17a378b42b57f6aaaed0e9be2de0bcafd84c88c4c3afa65b` | 11700 |
| `./uma_build_v4/uma/rsls/srb.py` | `551dee932fc9fef2ccb4cc7cc6e980b9ed1311de81e6f07be43939d99ddc987d` | 13343 |
| `./uma_build_v4/uma/rsls/stage3.py` | `6b1f817a8b8e9b102d5daffa69285b03933f4620b640ac82bb2478c42d3f3daf` | 10975 |
| `./uma_build_v4/uma/rsls/stage6.py` | `790160a4cf008ea059fd02fb0fbf796bf92c646b87a6ca5b6a985ac3464455b8` | 21208 |
| `./uma_build_v4/uma/semantic/__init__.py` | `2910d307a9ad0587408cf08d53f099006240277c8b6416fad5f6c65a4f6589d7` | 2864 |
| `./uma_build_v4/uma/semantic/constants.py` | `75a89b7b5f5dd7077ad4d82f7c956cb94143667b89599d65a356b68ab4dc5cb1` | 3961 |
| `./uma_build_v4/uma/semantic/constraints.py` | `e9d92e8bbbf0ea24a426e04edb392a6d42b3befe422bb39c7eae796fe5d144fc` | 12180 |
| `./uma_build_v4/uma/semantic/engine.py` | `483f43699dc5906d82acad1325ff1a84f6a16c320bb79231adcea5afe20aa3fe` | 9733 |
| `./uma_build_v4/uma/semantic/executor.py` | `272639bc7f28b21cfeaa8616edbcbfb10070ca62f8f69a51e7c3a25d59ed6777` | 5096 |
| `./uma_build_v4/uma/semantic/friction.py` | `718b3759e46bb01d90e2edfc37ffac3c459b471db3cecc278ff22df22523f15a` | 7889 |
| `./uma_build_v4/uma/semantic/inarticulation.py` | `3a28d5f0ddda19af32b4a711efce63ef6e626128735f89e1a25e11953fc01e62` | 8547 |
| `./uma_build_v4/uma/semantic/ir.py` | `95de7c876c112ca3cbfc01bc580eccefdf3a7f2958c09b2227741cdb1bba0270` | 1599 |
| `./uma_build_v4/uma/sphere/__init__.py` | `edcae7a6e07b0aa4c528a60d1107b339ffd27a022932732ee3d0df7cd8d32102` | 532 |
| `./uma_build_v4/uma/sphere/field.py` | `2255cf2c32f1c592751d825badff78c79256f916fdff7ee8fb46ff5fad8adeff` | 7589 |
| `./uma_build_v4/uma/sphere/geometry.py` | `022ec1e8af7656563e9cd9e54afc9332c7672056c5716586b00d4779369a85c7` | 7437 |
| `./uma_build_v4/uma/venturi/__init__.py` | `b12b1133e3999be29c69d22fecbdcbb8dfe5de7ae21bdde4fc21d682aaaa6655` | 643 |
| `./uma_build_v4/uma/venturi/injector.py` | `90a648253a01f201f3353ec006431096ede82dd0ddfa5a70db88377340ef14ee` | 1525 |
| `./uma_build_v4/uma/venturi/operator.py` | `9eaa142ce18fcfe1f4ef425a9ac71f602d55f89c8b5c43ddca74b3736ff64cdd` | 7984 |


**`33e3394` — Show what reading a document actually looks like** (1 files)

| Path | SHA-256 (current) | Bytes |
|---|---|---|
| `./README.md` | `a994706923621e28edbf46a21b4dbedc81e708e5060cabe7d1211a0a5644ad3a` | 10606 |



**2026-08-19 — the chaos claim withdrawn in the documents, and three gates repaired** (11 files)

`MANIFEST.sha256` is not edited; these are the current hashes.

Code:
- `uma/rsls/stage6.py` — `adaptive_dt` and `density_floor` added, both default
  OFF so every published number reproduces bit for bit. Fixed `dt` violated
  CFL by ~548x by step 8000; without a floor the run stalls at t ~ 3.34.
- `uma/rsls/ligo_lisa.py` — the echo prediction could not recover its own
  injection. Forward and inverse used length conventions differing by
  M_adm = 30, the search window `[0.002, 0.2]` s excluded the true spacing
  (~1.2-1.45 ms) for every admissible ell_star, and autocorrelation cannot
  separate the comb from the 250 Hz carrier over that lag range. Now cepstral;
  injected ell_*/M of 0.3, 0.6, 0.9 recover exactly. Added a timing-resolution
  floor so an unresolvable value REFUSES instead of reporting "inconsistent".
- `uma/rsls/memory.py` — `nec_violation` discarded its contraction and returned
  min((k.grad M)^2), a square, so it could not fail. Now contracts a genuinely
  null vector in (2+1) Minkowski, where the identity has content.
- `uma/rsls/frame_dragging.py` — cone compression `eta` was assigned 0.99 for
  saturated cells with `change_rate` computed and never read. It now refuses.

Tests: `test_ligo_lisa.py` +4 round-trip gates including the cepstrum-vs-ACF
control; `test_rsls.py` +3 NEC gates including a non-null contraction that must
go negative.

Documents: PRESENTATION.md, TOTALITY_OF_THEORY.md,
PROOF_AND_FALSIFICATION_CHECKPOINTS.md, BUILD_STATE.md and FRAMEWORK_MAP.md
still presented lambda = +1.127 and +19.4 as verified while the code, the tests
and IMPASSES.md had withdrawn them. Checkpoint N8 cited a test that no longer
exists. Corrected; BUILD_STATE.md is annotated rather than rewritten because it
is a dated log.

| Path | SHA-256 (current) | Bytes |
|---|---|---|
| `./uma_build_v4/BUILD_STATE.md` | `db6a3f820f96a63941371f622135d6497f07f1f27f721f90b51430254956b812` | 8625 |
| `./uma_build_v4/FRAMEWORK_MAP.md` | `b1358981e463000f3219e199e2ffc359d06915466ead0be66aa2b6880b135c78` | 15188 |
| `./uma_build_v4/PRESENTATION.md` | `b30023aa49aa4f9509618c21439970bb1a3ee67d998977c976b726d2711fe4c7` | 8646 |
| `./uma_build_v4/docs/PROOF_AND_FALSIFICATION_CHECKPOINTS.md` | `57cf35b15d48d9c2b002dd7b6a3d277efa695f2d337b7ba45baf671d6cc11661` | 12139 |
| `./uma_build_v4/docs/TOTALITY_OF_THEORY.md` | `32f95a75a2ac90a6325d1cf7eec559be35dac9be8207e71d5fa572d1ef1885b1` | 13648 |
| `./uma_build_v4/tests/test_ligo_lisa.py` | `3d78ca7b9e05d7f0d8ddde702b53391af788e61a0f1ffc1f19302cf4e783eda5` | 7550 |
| `./uma_build_v4/tests/test_rsls.py` | `96437d065ed952189594c9c35787add1a383c08d819672de455b532e0a5414ad` | 12206 |
| `./uma_build_v4/uma/rsls/frame_dragging.py` | `0b8cb5bd5d74e62d0eaf474442a7917877a8f4389f8d16fa1cd72ff598816f94` | 27281 |
| `./uma_build_v4/uma/rsls/ligo_lisa.py` | `351cc213a8ea6ca519a0fc1ae153968d9d13c253e99add3b8d3af42ef91bb169` | 17940 |
| `./uma_build_v4/uma/rsls/memory.py` | `bc3c086fde5b1821ba64fd86ea882da1de90fb01df7b9079ef382117f18a985e` | 11893 |
| `./uma_build_v4/uma/rsls/stage6.py` | `6e149064497e17d00883d8cd35e217181025bbb95896a859c5c372136afdb393` | 22754 |
