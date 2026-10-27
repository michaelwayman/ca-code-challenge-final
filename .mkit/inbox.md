# Inbox

- [ ] I1 2026-10-27 adjust: R16 bullet 'both service Dockerfiles install cauth and pin exact version in requirements' unverifiable in B1: no service Dockerfiles exist until B3 (auth) and B6 (main app). Pin cauth==0.1.0 there, then mkit done R16
- [ ] I2 2026-10-27 adjust: assumed claims version N=2 (accepts 1,2) in cauth so N-1 is testable; auth service must issue version 2; IsEditor relies on JWTAuthentication first for 401; library now depends on djangorestframework
