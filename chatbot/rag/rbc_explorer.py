import os
import glob
from pathlib import Path
from dotenv import load_dotenv
import shutil

# Load environment variables
load_dotenv()

class S2MExplorer:
    def __init__(self, output_folder="./test_documents", delay=2):
        self.output_folder = output_folder
        self.delay = delay
        self.visited_urls = set()
        self.document_urls = set()
        self.queue = []
        self.domains = ["S2M.com", "S2M.com", "S2M.com"]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
    
    def is_valid_url(self, url):
        """Keep for compatibility - not used in local mode"""
        return False
    
    def is_relevant_page(self, url, soup):
        """Keep for compatibility - not used in local mode"""
        return False
    
    def download_document(self, url):
        """Keep for compatibility - not used in local mode"""
        pass
    
    def explore_page(self, url):
        """Keep for compatibility - not used in local mode"""
        pass
    
    def scan_local_documents(self):
        """Scan the local documents folder for supported files"""
        print(f"Scanning local documents in: {self.output_folder}")
        
        if not os.path.exists(self.output_folder):
            print(f"Warning: Documents folder '{self.output_folder}' does not exist.")
            return []
        
        # Supported file extensions
        valid_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt']
        found_documents = []
        
        # Find all supported document files
        for extension in valid_extensions:
            pattern = os.path.join(self.output_folder, f"**/*{extension}")
            files = glob.glob(pattern, recursive=True)
            found_documents.extend(files)
        
        # Remove duplicates and sort
        found_documents = list(set(found_documents))
        found_documents.sort()
        
        # Add to document_urls set (using local paths instead of URLs)
        for doc in found_documents:
            self.document_urls.add(doc)
        
        return found_documents
    
    def get_document_info(self, filepath):
        """Get information about a local document file"""
        try:
            file_stats = os.stat(filepath)
            file_size = file_stats.st_size
            file_name = os.path.basename(filepath)
            file_ext = os.path.splitext(filepath)[1].lower()
            
            # Convert size to human readable format
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            return {
                'name': file_name,
                'path': filepath,
                'extension': file_ext,
                'size': size_str,
                'size_bytes': file_size
            }
        except Exception as e:
            print(f"Error getting info for {filepath}: {e}")
            return None
    
    def process_documents_for_rag(self, force_rebuild=False):
        """Process documents and build/rebuild the RAG vector store"""
        try:
            from chatbot.rag.document_loader import load_documents, split_documents
            from chatbot.rag.vector_store import create_vector_store
            from chatbot.config import VECTOR_DB_DIR
            
            print("\n" + "="*70)
            print("PROCESSING DOCUMENTS FOR RAG SYSTEM")
            print("="*70)
            
            # Check if vector store already exists
            if os.path.exists(VECTOR_DB_DIR) and not force_rebuild:
                print(f"Vector store already exists at: {VECTOR_DB_DIR}")
                rebuild = input("Do you want to rebuild it? (y/N): ").lower().strip()
                if rebuild != 'y':
                    print("Keeping existing vector store.")
                    return True
                else:
                    print("Rebuilding vector store...")
                    shutil.rmtree(VECTOR_DB_DIR)
            
            # Load documents using your existing loader
            print(f"Loading documents from: {self.output_folder}")
            documents = load_documents(self.output_folder)
            
            if not documents:
                print("❌ No documents found to process!")
                return False
            
            print(f"✅ Loaded {len(documents)} document pages")
            
            # Split documents into chunks
            print("Splitting documents into chunks...")
            chunks = split_documents(documents)
            
            if not chunks:
                print("❌ No chunks created from documents!")
                return False
            
            print(f"✅ Created {len(chunks)} chunks")
            
            # Create vector store with the chunks
            print("Creating vector store (this may take a few minutes)...")
            create_vector_store(chunks, VECTOR_DB_DIR)
            
            print("✅ Vector store created successfully!")
            print(f"📁 Vector store location: {VECTOR_DB_DIR}")
            
            # Test the vector store
            print("\nTesting vector store...")
            self._test_vector_store()
            
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure your RAG modules are properly installed and available.")
            return False
        except Exception as e:
            print(f"❌ Error processing documents for RAG: {e}")
            return False
    
    def _test_vector_store(self):
        """Test the vector store to make sure it's working"""
        try:
            from chatbot.rag.vector_store import load_vector_store
            from chatbot.config import VECTOR_DB_DIR
            
            vector_store = load_vector_store(VECTOR_DB_DIR)
            
            # Test query
            test_query = "account balance"
            docs = vector_store.similarity_search(test_query, k=2)
            
            print(f"✅ Vector store test successful!")
            print(f"   Query: '{test_query}'")
            print(f"   Found: {len(docs)} relevant documents")
            
            if docs:
                print(f"   Sample result: {docs[0].page_content[:100]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Vector store test failed: {e}")
            return False
    
    def run(self, starting_urls=None, max_pages=100, build_rag=True):
        """Run the explorer on local documents with RAG processing option"""
        print("Running S2M Explorer in LOCAL MODE - no downloading will be performed")
        print("=" * 70)
        
        # Scan local documents
        local_documents = self.scan_local_documents()
        
        if not local_documents:
            print("❌ No documents found in the specified folder.")
            print(f"Please add S2M documents to: {os.path.abspath(self.output_folder)}")
            print("Supported formats: PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, TXT")
            return 0
        
        print(f"✅ Found {len(local_documents)} local document(s):")
        print("-" * 50)
        
        # Display information about each document
        valid_docs = 0
        for doc_path in local_documents:
            info = self.get_document_info(doc_path)
            if info:
                print(f"📄 {info['name']}")
                print(f"   Path: {os.path.relpath(info['path'])}")
                print(f"   Type: {info['extension'].upper()[1:]} | Size: {info['size']}")
                print()
                valid_docs += 1
        
        # Group by file type
        by_type = {}
        for doc_path in local_documents:
            ext = os.path.splitext(doc_path)[1].lower()
            if ext not in by_type:
                by_type[ext] = []
            by_type[ext].append(doc_path)
        
        print("📊 Documents by type:")
        for ext, docs in by_type.items():
            print(f"   {ext.upper()[1:]}: {len(docs)} file(s)")
        
        print(f"\nDocument scan complete. Found {valid_docs} valid documents.")
        
        # Process documents for RAG if requested
        if build_rag and valid_docs > 0:
            print("\n" + "="*50)
            print("BUILDING RAG SYSTEM")
            print("="*50)
            
            rag_success = self.process_documents_for_rag()
            
            if rag_success:
                print("\n🎉 SUCCESS! Your RAG system is ready!")
                print("\nYou can now:")
                print("1. Start your chatbot server")
                print("2. Ask questions about the document contents")
                print("3. The chatbot will use your local documents to answer")
                
                return valid_docs
            else:
                print("\n⚠️  Documents found but RAG system build failed.")
                print("You may need to check your dependencies or configuration.")
                return 0
        
        return valid_docs

def main():
    print("S2M Explorer - LOCAL DOCUMENTS MODE WITH RAG")
    print("This script will process existing documents and build the RAG system.")
    print("No downloading will be performed.\n")
    
    # Create and run the explorer
    explorer = S2MExplorer()
    
    print("Options:")
    print("1. Scan documents and build RAG system (recommended)")
    print("2. Scan documents only (no RAG processing)")
    print("3. Rebuild RAG system (if documents already processed)")
    
    choice = input("\nChoose option (1-3): ").strip()
    
    if choice == "1":
        num_docs = explorer.run(build_rag=True)
    elif choice == "2":
        num_docs = explorer.run(build_rag=False)
    elif choice == "3":
        if explorer.scan_local_documents():
            success = explorer.process_documents_for_rag(force_rebuild=True)
            num_docs = len(explorer.document_urls) if success else 0
        else:
            num_docs = 0
    else:
        print("Invalid choice. Running default option (scan + build RAG)...")
        num_docs = explorer.run(build_rag=True)
    
    if num_docs > 0:
        print(f"\n✅ Success! {num_docs} documents processed.")
        print("\n🚀 Next steps:")
        print("1. Start your MCP server: python -m chatbot.mcp.server-sse_1")
        print("2. Start your web app: python app.py")
        print("3. Ask questions about your documents!")
    else:
        print("\n❌ No documents were processed. Please check your setup.")
        print("\n📁 To get started:")
        print("1. Create the 'test_documents' folder if it doesn't exist")
        print("2. Add your S2M documents (PDF, DOCX, TXT, etc.) to the folder")
        print("3. Run this script again to process them")

if __name__ == "__main__":
    main()