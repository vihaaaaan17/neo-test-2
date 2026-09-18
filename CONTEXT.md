# Glossary

## Export Bundle
A portable, polyglot `.zip` archive containing a workspace's entire canonical state, extracted text chunks, and metadata. 
- **Analytical dump**: It is designed to be loaded into Pandas, Jupyter, or another agentic framework to prevent vendor lock-in, rather than being a rigid 1-to-1 backup for bidirectional restoration.
- **Polyglot format**: Uses `.json` for hierarchical metadata and `.parquet` for large tabular arrays (e.g., embeddings, source chunks).
- **Scope**: By default, the bundle contains only structured metadata and extracted content. Raw binaries (e.g., source PDFs) are optionally referenced via signed URLs rather than packaged into the zip to prevent archive bloat.
