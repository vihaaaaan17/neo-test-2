from typing import Any
from app.schemas.block import DocumentBlockCreate

class ChunkingService:
    def process_docling_output(self, doc_dict: dict[str, Any]) -> list[DocumentBlockCreate]:
        """
        Takes the raw dictionary output from Docling and converts it into 
        DocumentBlockCreate schemas, preserving sequence and page numbers.
        """
        blocks = []
        
        # Mock output handling for testing
        if "text" in doc_dict and len(doc_dict) == 1:
            blocks.append(DocumentBlockCreate(
                block_type="text",
                sequence=1,
                text_or_ref=doc_dict["text"],
                page_number=1,
                metadata_={}
            ))
            return blocks
            
        sequence = 1
        
        # Docling extracts into 'texts'
        texts = doc_dict.get("texts", [])
        for item in texts:
            text_content = item.get("text", "")
            if not text_content:
                continue
                
            page_no = None
            if "prov" in item and item["prov"]:
                page_no = item["prov"][0].get("page_no")
                
            blocks.append(DocumentBlockCreate(
                block_type="text",
                sequence=sequence,
                text_or_ref=text_content,
                page_number=page_no,
                metadata_={"label": item.get("label")}
            ))
            sequence += 1
            
        return blocks
