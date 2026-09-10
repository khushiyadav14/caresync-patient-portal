# caresync-patient-portal
A hospital patient portal built during the CareSync 22-Day Program
# CareSync Hospital Management System

## Project Overview

CareSync is a Hospital Management System that helps manage hospital data in one place. The project provides a dashboard to view patients, doctors, appointments, and other hospital information. It uses APIs to connect the backend database with the dashboard.

## Technology Stack

The project uses the following technologies:

- Python
- FastAPI
- MySQL
- Vue.js
- Chart.js

## API Endpoints

The following API endpoints have been built for the CareSync project:

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Checks whether the CareSync API is running. |
| GET | `/patients` | Gets the list of all patients. |
| GET | `/doctors` | Gets the list of all doctors. |
| GET | `/appointments` | Gets the list of appointments. |
| GET | `/dashboard/summary` | Gets summary information for the dashboard. |
| GET | `/dashboard/patient-stats` | Gets patient statistics for dashboard charts. |
| GET | `/dashboard/appointment-stats` | Gets appointment statistics for dashboard charts. |

> Add any other endpoints your group has created to this table.

## How to Run

### Step 1: Clone the Repository

```bash
git clone https://github.com/khushiyadav14/caresync-patient-portal.git