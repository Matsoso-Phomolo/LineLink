# LineLink Product Overview

LineLink helps landlords manage Roma and NUL area line-houses remotely while helping room seekers find vacant rooms without walking around the village.

## Problem

Room seekers often discover vacancies by physically asking around. Landlords and caretakers manage tenants, rent, applications, and maintenance through informal calls, messages, and paper records. LineLink brings those workflows into one controlled system.

## Key Features

- Public vacant room finder
- Landlord property and room management
- Tenant onboarding by application and landlord approval
- Occupancy tracking
- Rent dues and payment submissions
- Support tickets and maintenance visibility
- Notifications and audit logs
- Role-based access control for admins, landlords, caretakers, and tenants

## Roles

- Admin: platform oversight
- Landlord: owns properties, rooms, listings, tenants, payments, and applications
- Caretaker: acts within an assigned landlord/property scope
- Tenant: sees only their own tenant portal data
- Public visitor: browses public listings and applies for a specific room

## Public Room Finder

Public users can browse vacant rooms, filter by location, price, room type, and room size, view details, request a viewing, and apply for a specific listing.

## Tenant Onboarding Workflow

1. Public user finds a vacant room listing.
2. User applies under that exact listing.
3. The application is tied to `listing_id`, `room_id`, `property_id`, and `landlord_id` through the listing.
4. Landlord or assigned caretaker reviews the application.
5. Approval can lead to tenant account creation or linking.
6. Assignment creates an occupancy, marks the room occupied, hides the listing, and starts rent dues.

## Multi-Tenant Security

LineLink treats every line-house or apartment as belonging to one landlord. Landlord and caretaker routes are filtered by landlord scope. Tenants can access only their own data. Public listings are the only public records.

## Deployment Overview

- Backend: FastAPI on Render with PostgreSQL and Alembic migrations.
- Frontend: React/Vite on Vercel.
- Secrets: provided through Render and Vercel environment variables, not committed to Git.

## Roadmap

- Mobile app with React Native/Expo
- Lease documents and digital signatures
- SMS and email delivery for invitations
- Rich maintenance work orders
- Billing dashboard for platform subscriptions
- Room photos and document upload improvements
