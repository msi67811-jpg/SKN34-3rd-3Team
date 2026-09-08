ALTER TABLE rag_documents ADD COLUMN chunk_id VARCHAR(100) UNIQUE;
ALTER TABLE rag_documents ADD COLUMN policy_id INT REFERENCES policies(id);
ALTER TABLE rag_documents ADD COLUMN content TEXT;