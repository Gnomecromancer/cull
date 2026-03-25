# devcull TUI demo tape
# Records the interactive cache cleaner scanning ~/IdeaProjects

size: [130, 35]
gif_width: 1000
app_args:
  root: "."          # path to scan; change to your projects directory
  older_than: 0
  min_size_mb: 0

steps:
  # Wait for scan to complete and table to populate
  - sleep: 10.0
    capture: 2500

  # Navigate down through results
  - press: down
    sleep: 0.15
  - press: down
    sleep: 0.15
  - press: down
    sleep: 0.15
    capture: 1800

  # Select a few items
  - press: space
    sleep: 0.2
  - press: down
    sleep: 0.1
  - press: space
    sleep: 0.2
  - press: down
    sleep: 0.1
  - press: space
    sleep: 0.3
    capture: 2500
