import argparse
import logging
import os
from pathlib import Path
from planner import ResearchPlanner
from crawler import WebCrawler
from analyzer import ContentAnalyzer
from report import ReportGenerator
from utils.cache_manager import CacheManager
from utils.research_context import ResearchContext
from utils.recovery_manager import RecoveryManager
from utils.config import Config
from typing import Dict, List, Optional
from utils.progress_display import ResearchProgress
from datetime import datetime
from rich.console import Console
from concurrent.futures import ProcessPoolExecutor, as_completed
import traceback

class ResearchAgent:
    def __init__(self, config: Config):
        self.config = config
        self.planner = ResearchPlanner(config)
        self.crawler = WebCrawler(config)
        self.analyzer = ContentAnalyzer(config)
        self.report_gen = ReportGenerator(config)
        
        # Initialize utilities
        self.cache = CacheManager(cache_dir=config.cache_dir)
        self.recovery = RecoveryManager(config.output_dir)
        self.progress = ResearchProgress()
        self.console = Console()
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging for the research agent"""
        log_dir = Path(self.config.output_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "research.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def execute(self, query: str, output_dir: str):
        """Execute research with recovery support"""
        context = None
        try:
            # Initialize or recover context
            self.progress.update("Initializing research context")
            context = self._initialize_context(query, output_dir)
            self.logger.info(f"Starting research for query: {query}")
            
            # Generate or recover plan
            self.progress.update("Generating research plan", f"Query: {query}")
            plan = self._get_or_generate_plan(query, context)
            self.logger.info("Research plan generated")
            
            # Gather sources
            self.progress.update("Gathering sources", "Searching and analyzing web content")
            sources = self._gather_sources(plan, context)
            self.logger.info(f"Gathered {len(sources)} sources")
            
            # Analyze sources
            self.progress.update("Analyzing sources", f"Processing {len(sources)} documents")
            analyzed_data = self._analyze_sources(sources, context)
            self.logger.info("Source analysis completed")
            
            # Generate report
            self.progress.update("Generating report", "Creating final research document")
            # Get response language from plan
            response_language = plan.get('response_language', 'en')
            # Create language-specific folder name
            folder_name = "research_report"
            if response_language != 'en':
                folder_name = f"{folder_name}_{response_language}"
            output_path = os.path.join(output_dir, folder_name, f"{datetime.now():%Y%m%d_%H%M%S}")
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            self.report_gen.generate_report(analyzed_data, output_path)
            self.logger.info("Report generation completed")
            
            # Cleanup and complete
            self.recovery.clear_checkpoint()
            context.update_status("completed")
            self.progress.complete(output_path)
            
        except Exception as e:
            error_context = f"Step: {self.progress.current_step}"
            if self.progress.current_details:
                error_context += f"\nDetails: {self.progress.current_details}"
                
            self.logger.error(
                f"Research failed: {str(e)}\n"
                f"Context: {error_context}\n"
                f"Traceback:\n{traceback.format_exc()}"
            )
            self.progress.show_error(e, error_context)
            if context:
                self._handle_failure(context, e)
            raise
            
    def _get_or_generate_plan(self, query: str, context: ResearchContext) -> Dict:
        """Get plan from cache or generate new one"""
        cache_key = f"plan_{query}"
        plan = self.cache.get(cache_key)
        
        if plan:
            self.logger.info("Using cached research plan")
            self._display_plan(plan)
            context.plan = plan  # Store plan in context
            return plan
            
        self.logger.info("Generating new research plan")
        plan = self.planner.generate_plan(query)
        self._display_plan(plan)
        self.cache.set(cache_key, plan)
        context.plan = plan  # Store plan in context
        return plan
        
    def _display_plan(self, plan: Dict):
        """Display research plan for debugging"""
        self.console.print("\n[bold blue]Research Plan:[/]")
        self.console.print("[yellow]Primary Search Queries:[/]")
        for query in plan['primary_search_queries']:
            self.console.print(f"  • {query}")
            
        self.console.print("\n[yellow]Required Sections:[/]")
        for section in plan['required_sections']:
            self.console.print(f"  • {section['title']}")
            for point in section['key_points']:
                self.console.print(f"    - {point}")
                
        self.console.print("\n[yellow]Analysis Steps:[/]")
        for step in plan['analysis_steps']:
            self.console.print(f"  • {step['step']} (Priority: {step['priority']})")
            
    def _gather_sources(self, plan: Dict, context: ResearchContext) -> List[Dict]:
        """Gather sources in parallel"""
        try:
            self.console.print("\n[bold blue]Source Gathering:[/]")
            sources = []
            
            # Get all URLs from search results
            urls_to_process = []
            for query, results in plan['search_results'].items():
                for result in results:
                    try:
                        if self._is_valid_source(result):
                            urls_to_process.append((result['link'], result, len(urls_to_process) + 1))
                    except KeyError as e:
                        self.logger.error(f"Invalid result structure: {result}")
                        self.logger.error(f"Missing key: {str(e)}")
                        continue
            
            total_urls = len(urls_to_process)
            self.progress.update("Gathering sources", f"Processing {total_urls} URLs in parallel")
            
            # Process URLs in parallel
            with ProcessPoolExecutor(max_workers=self.config.max_threads) as executor:
                # Submit processing tasks
                future_to_url = {
                    executor.submit(
                        self.crawler.process_url, 
                        url,
                        self.cache  # Pass cache manager
                    ): (metadata, index)
                    for url, metadata, index in urls_to_process
                }
                
                # Process results as they complete
                for future in as_completed(future_to_url):
                    metadata, index = future_to_url[future]
                    try:
                        content = future.result()
                        if content:
                            self._display_source_result(metadata, content, index, total_urls)
                            sources.append({
                                'metadata': metadata,
                                'content': content
                            })
                            context.add_source(metadata)
                    except Exception as e:
                        self.logger.error(f"Error processing URL {metadata['link']}: {str(e)}")
                        self.console.print(f"[red]Error processing URL {metadata['link']}: {str(e)}[/]")
            
            return sources
            
        except Exception as e:
            self.logger.error(f"Error in source gathering: {str(e)}\nResult data: {plan['search_results']}")
            raise
        
    def _display_source_result(self, metadata: Dict, content: Dict, index: int, total: int):
        """Display source processing result"""
        self.console.print(f"\n[yellow]Source {index}/{total}:[/] {metadata['link']}")
        self.console.print(f"[blue]Type:[/] {metadata.get('source_type', 'unknown')}")
        
        # Show content excerpt
        excerpt = content['content'][:200] + "..." if len(content['content']) > 200 else content['content']
        self.console.print("[green]Content Preview:[/]")
        self.console.print(excerpt)
        
        if content.get('needs_visual'):
            self.console.print("[magenta]Visual content detected[/]")
            
        self.console.print("[dim]" + "-"*50 + "[/]")
        
    def _analyze_sources(self, sources: List[Dict], context: ResearchContext) -> Dict:
        """Analyze gathered sources with parallel processing"""
        self.console.print("\n[bold blue]Source Analysis:[/]")
        analyzed_sources = []
        
        # Get query from context
        query = context.query if hasattr(context, 'query') else ""
        
        # Get response language from plan
        response_language = context.plan.get('response_language', 'en') if hasattr(context, 'plan') else 'en'
        
        # Split sources into batches for better efficiency
        batch_size = max(1, len(sources) // self.config.max_threads)
        source_batches = [
            sources[i:i + batch_size] 
            for i in range(0, len(sources), batch_size)
        ]
        
        # Process batches in parallel using multiple processes
        with ProcessPoolExecutor(max_workers=self.config.max_threads) as executor:
            # Submit batch analysis tasks
            future_to_batch = {
                executor.submit(
                    self.analyzer.process_batch, 
                    batch,
                    self.config.openai_key,
                    self.cache,  # Pass cache manager
                    query,  # Pass query for relevance filtering
                    response_language  # Pass language for response
                ): (batch, i)
                for i, batch in enumerate(source_batches)
            }
            
            # Process results as they complete
            for future in as_completed(future_to_batch):
                batch, batch_index = future_to_batch[future]
                try:
                    analysis = future.result()
                    if analysis:
                        analyzed_sources.append(analysis)
                        # Display progress for the batch
                        self._display_batch_analysis(analysis, batch_index)
                except Exception as e:
                    self.logger.error(f"Error analyzing batch {batch_index}: {str(e)}")
                    self.console.print(f"[red]Error analyzing batch {batch_index}: {str(e)}[/]")
        
        # Combine all analyses with language setting
        return self.analyzer.synthesize_findings(analyzed_sources, response_language)
        
    def _display_batch_analysis(self, analysis: Dict, batch_index: int):
        """Display analysis results for a batch"""
        self.console.print(f"\n[yellow]Batch {batch_index + 1}:[/]")
        
        # Display source summaries
        for i, source in enumerate(analysis['sources'], 1):
            self.console.print(f"\n[green]Source {i}:[/] {source['link']}")
            
        # Show excerpt of analysis
        self.console.print("\n[blue]Analysis Summary:[/]")
        self.console.print(analysis['summary'][:500] + "...")
        
        if 'visual_analysis' in analysis:
            self.console.print("\n[blue]Visual Analysis:[/]")
            self.console.print(analysis['visual_analysis'][:500] + "...")
            
        self.console.print("\n[dim]" + "-"*50 + "[/]")
        
    def _is_valid_source(self, result: Dict) -> bool:
        """Check if source should be included"""
        return (
            result.get('source_type') in ['academic', 'research_paper', 'official'] or
            (result.get('source_type') == 'article' and self._is_recent(result))
        )
        
    def _is_recent(self, result: Dict) -> bool:
        """Check if source is recent enough"""
        if not result.get('date'):
            return True  # Include if no date available
        # Add date checking logic here if needed
        return True
        
    def _initialize_context(self, query: str, output_dir: str) -> ResearchContext:
        """Initialize or recover research context"""
        checkpoint = self.recovery.load_checkpoint()
        if checkpoint:
            self.logger.info("Recovering from checkpoint")
            context = ResearchContext(query, output_dir)
            context.sources = checkpoint.get('sources', [])
            context.current_section = checkpoint.get('current_section')
            context.status = checkpoint.get('status', 'recovered')
            return context
            
        self.logger.info("Starting new research context")
        return ResearchContext(query, output_dir)
        
    def _handle_failure(self, context: ResearchContext, error: Exception):
        """Handle research failure"""
        if context:
            context.update_status("failed", {"error": str(error)})
            # Save checkpoint for recovery
            self.recovery.save_checkpoint({
                "query": context.query,
                "status": context.status,
                "sources": context.sources,
                "current_section": context.current_section
            })

def main():
    parser = argparse.ArgumentParser(description="Deep Research Agent")
    parser.add_argument("--query", required=True, help="Research query to investigate")
    parser.add_argument("--output-dir", default="./reports", help="Directory for output files")
    args = parser.parse_args()
    
    try:
        # Load and validate configuration
        config = Config.from_env()
        config.validate()
        
        # Update output directory from args
        config.output_dir = args.output_dir
        
        # Initialize and run agent
        agent = ResearchAgent(config)
        agent.execute(args.query, args.output_dir)
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)
    except Exception as e:
        print(f"Research failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 