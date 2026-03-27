#!/usr/bin/env python3
"""
Main demo script for the selected features:
1. PDF Summarization
2. PowerPoint Summarization  
3. Web scraping from papers.codechefvit.com
4. Question extraction from PDFs
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from ai.pdf_sum import summarize_pdf
from ai.ppt_sum import summarize_pptx
from ai.agent.scraper import ExamScraper
from ai.agent.extractor import QuestionExtractor
from ai.agent.m import setup_directories, print_info, print_success, print_error

def main():
    print("=== VIT Exam Paper Processing Tool ===")
    print("Available features:")
    print("1. PDF Summarization")
    print("2. PowerPoint Summarization")
    print("3. Scrape Papers from CodeChef VIT")
    print("4. Extract Questions from PDFs")
    print("5. Exit")
    
    # Setup directories
    setup_directories()
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                print_info("Starting PDF Summarization...")
                summarize_pdf()
                
            elif choice == "2":
                print_info("Starting PowerPoint Summarization...")
                summarize_pptx()
                
            elif choice == "3":
                print_info("Starting Paper Scraping...")
                scraper = ExamScraper()
                
                # Get subject from user
                subject = input("Enter subject (e.g., 'Computer Science', 'Mathematics', 'Physics'): ").strip()
                if not subject:
                    subject = "Computer Science"
                
                # Get optional topic
                topic = input("Enter specific topic (optional, press Enter to skip): ").strip() or None
                
                # Get max papers
                try:
                    max_papers = int(input("Maximum papers to download (default 5): ").strip() or "5")
                except ValueError:
                    max_papers = 5
                
                print_info(f"Scraping papers for subject: {subject}")
                papers = scraper.scrape_papers(subject, topic, max_papers)
                
                if papers:
                    print_success(f"Successfully downloaded {len(papers)} papers:")
                    for paper in papers:
                        print(f"  - {os.path.basename(paper)}")
                else:
                    print_error("No papers were downloaded")
                
            elif choice == "4":
                print_info("Starting Question Extraction...")
                extractor = QuestionExtractor()
                
                # Check for PDFs in data/raw_papers
                pdf_dir = Path("data/raw_papers")
                if not pdf_dir.exists():
                    pdf_dir.mkdir(parents=True, exist_ok=True)
                    print_error(f"No PDFs found in {pdf_dir}")
                    print_info("Please download some papers first using option 3")
                    continue
                
                pdf_files = list(pdf_dir.glob("*.pdf"))
                if not pdf_files:
                    print_error(f"No PDF files found in {pdf_dir}")
                    print_info("Please download some papers first using option 3")
                    continue
                
                print_info(f"Found {len(pdf_files)} PDF files:")
                for i, pdf in enumerate(pdf_files, 1):
                    print(f"  {i}. {pdf.name}")
                
                # Get topic filter
                topic = input("Enter topic to filter questions (optional, press Enter to skip): ").strip() or None
                
                # Extract questions from all PDFs
                file_paths = [str(pdf) for pdf in pdf_files]
                results = extractor.extract_from_multiple_papers(file_paths, topic)
                
                print_success(f"Processed {results['papers_processed']} papers")
                print_info(f"Total unique questions extracted: {results['unique_questions']}")
                
                # Save results
                output_file = f"outputs/extracted_questions_{topic or 'all'}.json"
                extractor.save_questions(results['combined_questions'], topic or 'all', 'VIT Exam Papers', output_file)
                print_success(f"Results saved to {output_file}")
                
                # Show sample questions
                if results['combined_questions']:
                    print_info("\nSample extracted questions:")
                    for i, q in enumerate(results['combined_questions'][:3], 1):
                        print(f"  {i}. {q[:100]}...")
                
            elif choice == "5":
                print_info("Exiting...")
                break
                
            else:
                print_error("Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print_info("\nExiting...")
            break
        except Exception as e:
            print_error(f"Error: {e}")

if __name__ == "__main__":
    main()
