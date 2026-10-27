# Inbox

- [ ] I1 2026-10-27 adjust: R16 bullet 'both service Dockerfiles install cauth and pin exact version in requirements' unverifiable in B1: no service Dockerfiles exist until B3 (auth) and B6 (main app). Pin cauth==0.1.0 there, then mkit done R16
- [ ] I2 2026-10-27 adjust: assumed claims version N=2 (accepts 1,2) in cauth so N-1 is testable; auth service must issue version 2; IsEditor relies on JWTAuthentication first for 401; library now depends on djangorestframework
- [ ] I3 2026-10-27 bug: cauth.verify: non-hashable or bool/float version claim raises TypeError (500) or passes; require int and catch
- [ ] I4 2026-10-27 adjust: libs/README: say contract step = bump CLAIMS_VERSION
- [ ] I5 2026-10-27 adjust: cauth/roles.py added beyond R18-R20; keep
