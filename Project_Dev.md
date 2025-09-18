# Project Overview

This project will build a web-based visualization of ocean data from Argo floats. Argo is a global network of drifting sensors that record ocean temperature, salinity and other variables. Its data are published in NetCDF format[1]. Our application will fetch Argo data (e.g. by region/time) using free, open-source tools, process it, and display it in an interactive web interface. The system will be divided into clear modules (data ingestion, back-end API, front-end UI, etc.) to keep development simple and organized[2]. By following a structured software development process (planning, design, coding, testing, deployment)[3], we ensure each step builds on the previous ones.

**Data Source:** Core Argo profiles (ocean measurements) in NetCDF files[1]. We may also incorporate other open ocean/climate datasets if needed (e.g. NOAA ocean profile data), but the primary source is Argo.

**Goal:** Provide an interactive web app (map-based and/or charts) where users can view Argo float locations and data profiles. For example, the app might show a world map with float positions and allow clicking a float to see its temperature vs. depth graph.

**Tools & Tech:** Use free, open-source technologies. For example: Python (with Argopy/netCDF4) or Node.js for back-end data access; Node/Express or Python/Flask for APIs; JavaScript/HTML/CSS for front-end; Leaflet for interactive maps[4]; Chart.js or D3.js for plotting. All tools must have free tiers (no paid services). The prototype can run on localhost or a free hosting platform (GitHub Pages, Vercel, Heroku free tier, etc.).

## System Architecture

The system is organized into modules that mirror the software’s layers. This modular approach keeps components small and maintainable[2]. Each module has a clear responsibility and interface with others. Below is a high-level description of components:

### Data Ingestion Module
This module retrieves Argo NetCDF data and converts it into a usable form. For example, we will use the Argopy Python library, which provides a DataFetcher class to download Argo floats by region and time range in just a few lines[5]. Argopy returns an xarray.Dataset of Argo profiles (with latitude, longitude, time, temperature, salinity, etc.), simplifying data access[5]. This module can also fetch or preprocess any other required data sources.

### Data Processing Module (Backend)
Once raw data is retrieved, this module processes it into application-ready format. Tasks include filtering variables, cleaning or aggregating values, and saving intermediate results. For example, it might average profiles, convert units, or cache data in memory or a database. This module also sets up an API (Application Programming Interface) server. The back-end API exposes endpoints like `/api/floats?region=…&date=…` that return JSON data to the front-end. We might implement the API in Python (Flask/FastAPI) or Node.js (Express); both are free and popular for rapid prototyping.

### Front-End UI Module
The user interface runs in a web browser. It will include pages or components to display maps, charts, and controls. Using a mapping library like Leaflet[4], we can show an interactive map with markers for Argo float locations. When the user clicks a float, the UI can fetch detailed data from the backend and show a profile chart (e.g. temperature vs. depth using Chart.js). This module will consist of HTML/CSS layouts and JavaScript code. The front-end communicates with the back-end via HTTP (e.g. AJAX or Fetch API).

### Data Storage/Caching (Optional Module)
For performance, we may use a lightweight data store. Options include an in-memory cache, a local file (JSON/CSV), or a free database (e.g. SQLite). This helps avoid re-downloading large Argo files. If time allows, we can integrate a free multi-model database like ArangoDB (Argo + ArangoDB, pun intended) or just use simple file-based storage.

Each module is kept small and focused. For example, the Data Ingestion module only handles data retrieval (it does not contain mapping code). This makes it easier for one person (and AI tools) to work on modules independently and in parallel. By modularizing, we reduce complexity and make debugging simpler[2].

## Detailed Development Phases

Below we define clear phases of development. Each phase has goals, tasks, and deliverables. This roadmap aligns with a typical SDLC (Software Development Life Cycle) process[3] but tailored for a two-day hackathon schedule. Dependencies and hand-offs between phases are noted so work can flow smoothly.

### Phase 1: Planning & Requirements (Few hours) – Identify what the software must do.

**Goals:** Define scope, features, and constraints. Establish technology stack and data sources. Set milestones for the next two days.

**Tasks:**

- Gather Requirements: Decide exactly what the app should show. For example, “Display Argo float locations and temperature-depth plots.” Clarify any additional requirements (if the problem statement includes other datasets or features).
- Feasibility Check: Confirm that free data is available. Verify Argopy or NetCDF libraries are installable without cost[1].
- Outline User Stories: e.g. “As a user, I can see a map of all floats in region X.”
- Resource Planning: Since you are solo, estimate time and break down work. Identify any libraries or APIs needed (e.g. Leaflet, Chart.js, Argopy, netCDF4).
- Risk Assessment: Note potential issues (e.g. large data size, time needed to parse netCDF). Plan mitigations (use small sample data or fewer floats to start).

**Deliverables:** A short Project Plan or specification document summarizing features, scope and tech stack. This includes a rough sketch of system architecture and a list of data sources (e.g. Argo GDAC NetCDF files[1]). Even simple bullet points are fine. This plan guides all later work.

**Dependency:** This phase’s outputs (project plan, defined features) direct all subsequent design and coding. Without clear requirements, design would be unfocused[6].

### Phase 2: System Design (2–3 hours) – Define how to implement requirements before coding.

**Goals:** Create design artifacts that guide coding. Decide on software structure (modules, data flows, interfaces).

**Tasks:**

- Architecture Diagram: Sketch how modules connect (e.g. Data Module → Back-end → Front-end). You can draw a simple flowchart on paper or a whiteboard and/or describe it in text.
- API Design: List needed endpoints (e.g. GET /floats, /profiles). Define request/response formats (JSON structure).
- Data Model: Define how raw Argo data maps to the application. Decide which variables to extract (e.g. LATITUDE, LONGITUDE, TEMP, PSAL). Consider simplifying or filtering.
- UI Mockups: Roughly design the web interface. For instance, a homepage with a map, plus a profile panel. You can sketch this on paper or use free tools (e.g. draw.io).
- Choose Frameworks/Libraries: Finalize languages and libraries. E.g., React or plain JS? Chart.js for charts? Leaflet for maps (Leaflet is a leading open-source mapping library[4]).
- Document: Write a brief Software Design Document (SDD) summary of these decisions. Include diagrams if possible. This SDD “serves as a roadmap” during coding[7].

**Deliverables:** Architecture and design notes. The SDD outlines components, data flow, and UI plan. These decisions ensure all developers (even if just you + AI) have a blueprint to follow. For example, the SDD might detail that the back-end will use Flask and the front-end will call /api/floats?bbox=…. It specifies how modules depend on each other (e.g. front-end depends on back-end API).

**Dependency:** Implementation (Phase 3) will directly follow this design. The code must match the plan, or code may break if designs change midstream. Good design prevents rework[8].

### Phase 3: Implementation – Backend and Data (4–6 hours) – Write code to fetch and serve data.

**Goals:** Develop the back-end APIs and data processing logic. Get real data flowing through the system.

**Tasks:**

- Set Up Version Control: Initialize a Git repository (e.g. on GitHub) for code. Every new script or config should be committed.
- Environment Setup: Install required libraries. For Python: Argopy (pip install argopy) and NetCDF4, Flask/FastAPI, etc. For Node: netcdf or request libraries, Express, etc.
- Data Fetching Prototype: Write a small script using Argopy to fetch a subset of Argo data. For example, in Python:

    ```python
    import argopy
    ds = argopy.DataFetcher().region([-75, -45, 20, 30, 0, 10, '2020-01', '2020-02']).load().data
    print(ds)
    ```

    This should download some profiles and print their structure[5]. This validates data access.

- Data Parsing: Extract needed fields from the dataset (e.g. latitude, longitude, temperature, pressure). Store them in a simple in-memory structure (like a Python list of dicts) or a lightweight database.
- API Development: Implement the server. For example, create endpoints:

    - `GET /api/floats` – returns a list of floats/positions in a region or time range.
    - `GET /api/profile?float_id=xxx` – returns profile data for one float.

    The back-end should fetch or filter data as needed and return JSON. Test the endpoints using tools like Postman or curl.

- Modular Code: Keep data-fetching and API logic separate. For instance, one file handles netCDF loading, another handles HTTP routing. This follows the modular approach (each part handles one responsibility)[2].

**Deliverables:** Working back-end code with at least one endpoint. Example response: a JSON array of float records (each with latitude, longitude, timestamp, etc.). Verify with sample requests. This phase also includes basic input validation (e.g. check that coordinates are numbers) and error handling (e.g. return an error JSON if data isn’t found). Document the API endpoints in a README or in-code comments (so the front-end knows how to call them).

**Dependency:** The front-end (next phase) relies on these APIs. Ensure this stage is stable: if the back-end changes its API, update documentation and front-end accordingly.

<!-- More phases continue similarly -->

## References

- [1] Argo data | Argo  
  https://argo.ucsd.edu/data/
- [2] Modular Approach in Programming - GeeksforGeeks  
  https://www.geeksforgeeks.org/software-engineering/modular-approach-in-programming/
- [3][6][7][8][9] The Seven Phases of the Software Development Life Cycle  
  https://www.harness.io/blog/software-development-life-cycle-phases
- [4] Leaflet - a JavaScript library for interactive maps  
  https://leafletjs.com/
- [5] Fetching Argo data — argopy 1.3.0 documentation  
  https://argopy.readthedocs.io/en/latest/user-guide/fetching-argo-data/
