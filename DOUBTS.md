why are we storing/writing data/ responses ? to our local db?
=> {
    Why? Your project has an Analytics Dashboard (which is served at http://localhost:8000/analytics). When you visit that dashboard, the backend reads verification_events.json and calculates statistics like "Average Score", "Verdict Distribution", and "Pipeline Processing Times". If you don't store this data, your analytics dashboard will always be empty!
}

docker solves it -> mapping to to soem folder called data.
->we need to map  local data folder to the container's data folder using a "Volume"
---------------------------------------------------------------
NOTE:
Your API caching using cachetools in app/core/cache.py is entirely in-memory, so cache will be cleared when the container restarts. This is standard behavior and perfectly fine).
------------------------------------------------------