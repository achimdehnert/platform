"""
MCP Server Management Command
==============================

Start the BF Agent MCP Server.
"""

from django.core.management.base import BaseCommand
from bfagent.mcp.server import BFAgentMCPServer


class Command(BaseCommand):
    help = 'Run BF Agent MCP Server with Django Integration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--read-only',
            action='store_true',
            help='Start server in read-only mode'
        )
        parser.add_argument(
            '--pool-size',
            type=int,
            default=10,
            help='Connection pool size (default: 10)'
        )
        parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
    
    def handle(self, *args, **options):
        """Start the MCP server."""
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('🚀 Starting BF Agent MCP Server'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write()
        
        # Create server instance
        server = BFAgentMCPServer()
        
        # Apply options
        if options['read_only']:
            server.read_only = True
            self.stdout.write(self.style.WARNING('⚠️  Read-only mode enabled'))
        
        if options['pool_size']:
            server.pool_size = options['pool_size']
            self.stdout.write(f"📊 Connection pool size: {options['pool_size']}")
        
        self.stdout.write()
        
        # Show status
        status = server.status()
        self.stdout.write(self.style.SUCCESS('📋 Server Configuration:'))
        for key, value in status.items():
            self.stdout.write(f"   {key}: {value}")
        
        self.stdout.write()
        
        # Run server
        try:
            server.run()
        except KeyboardInterrupt:
            self.stdout.write()
            self.stdout.write(self.style.WARNING('🛑 Shutting down...'))
        except Exception as e:
            self.stdout.write()
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            raise
        finally:
            server.shutdown()
            self.stdout.write(self.style.SUCCESS('✅ MCP Server stopped'))
