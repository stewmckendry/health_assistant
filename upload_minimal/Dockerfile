FROM alpine:latest

# Create data directory structure
RUN mkdir -p /app/data/dr_off_agent/processed/dr_off \
    /app/data/dr_opa_agent \
    /app/data/processed/dr_opa \
    /app/data/processed/dr_off

# Copy database files
COPY data/*.db /app/data/
COPY data/dr_opa_agent/opa.db /app/data/dr_opa_agent/ 2>/dev/null || echo "Dr OPA agent DB skipped"
COPY data/processed/dr_opa/opa.db /app/data/processed/dr_opa/ 2>/dev/null || echo "Dr OPA processed DB skipped"

# Keep container running
CMD ["tail", "-f", "/dev/null"]