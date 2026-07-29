# RC1 Deployment Guide

## Pre-deployment

Deploy the frozen backend and frontend together with their existing dependency declarations. Confirm the database migration chain has head `0011`; this sprint introduces no migration. Keep capability feature settings disabled unless an approved rollout explicitly enables them.

## Controlled rollout

Enable backend framework/API/execution/governance controls only through the existing configuration process. Enable `NEXT_PUBLIC_CTV_ONE_CAPABILITIES_ENABLED=true` only for the intended frontend deployment after backend controls are approved. Verify an authenticated user can discover the capability route and that disabled controls return controlled errors.

## Rollback

Disable the frontend capability environment flag and the existing backend capability controls. No data migration or API rollback is required for RC1 because this release adds no persistence schema or contract change.
