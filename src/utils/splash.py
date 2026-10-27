"""
Filename: splash.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Splash screen module.

This module provides the ASCII art splash screen for the application.
Can be used by both the main application and setup script.
"""

from colorama import Fore, Style
import platform


def get_splash_screen() -> str:
    """Get application splash screen

    Returns:
        str: Formatted splash screen ASCII art
    """
    return f"""{Fore.CYAN}
                            🟦🟪
                        🟦🟪🟦🟪🟦🟪🟦
            🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦
🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪
🟪                                            \t\t🟦
🟦             █▀▀█ █▀▀▄ █▀▀▄ █▀▀█ █▀▀█ █▀▀█  \t\t🟪
🟪             █▄▄█ █  █ █  █ █▄▄█ █▄▄▀ █▄▄▀  \t\t🟦
🟦             ▀  ▀ ▀▀▀  ▀▀▀  ▀  ▀ ▀ ▀▀ ▀ ▀▀  \t\t🟪
🟪                                            \t\t🟦
🟦             ✨ 【 REFRESH EDITION 】✨    \t\t🟪
🟪                                            \t\t🟦
🟦                                            \t\t🟪
🟪     {Fore.LIGHTBLUE_EX}📚 Organize  🔍 Search  💾 Download  🔔 Notify{Style.RESET_ALL} \t🟦
🟦                                            \t\t🟪
🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪
            🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦🟪🟦
                        🟦🟪🟦🟪🟦🟪🟦
                            🟦🟪

    {Style.RESET_ALL}"""


def show_splash_screen():
    """Display the splash screen"""
    print(get_splash_screen())


def show_version():
    """Show version information"""
    version = "1.0.0"  # You might want to get this from a version file or package metadata
    print(f"\n{Fore.CYAN}Addarr Version: {version}")
    print(f"{Fore.CYAN}{'═' * 50}")
    print(f"{Fore.GREEN}🚀 A Telegram bot for media management")
    print(f"{Fore.CYAN}Repository: {Fore.BLUE}https://github.com/cyneric/addarr")
    print(f"{Fore.CYAN}Documentation: {Fore.BLUE}https://github.com/cyneric/addarr/wiki")
    print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}\n")


def show_welcome_screen():
    """Show the main application welcome screen with system info and commands"""
    # Imported here so the setup wizard can use this module without loading config.yaml
    from src.config.settings import config

    # System information
    python_version = platform.python_version()
    system_info = platform.platform()

    # Configuration information from logging and security settings
    debug_mode = "✅ Enabled" if config.get("logging", {}).get("debug", False) else "❌ Disabled"
    admin_mode = "✅ Enabled" if config.get("security", {}).get("enableAdmin", False) else "❌ Disabled"
    language = config.get("language", "en-us")

    # Print welcome message
    print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🚀 Addarr Bot{Style.RESET_ALL} - Media Management Made Easy")
    print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")

    print(f"\n{Fore.YELLOW}📊 System Information:{Style.RESET_ALL}")
    print(f"• 🐍 Python Version: {python_version}")
    print(f"• 💻 Operating System: {system_info}")

    print(f"\n{Fore.YELLOW}⚙️ Configuration:{Style.RESET_ALL}")
    print(f"• 🐛 Debug Mode: {debug_mode}")
    print(f"• 👑 Admin Mode: {admin_mode}")
    print(f"• 🌐 Language: {language}")

    print(f"\n{Fore.YELLOW}💻 Command Line Interface:{Style.RESET_ALL}")
    print("• 🚀 python run.py - Start the bot normally (on first run, setup wizard will start automatically)")
    print("• 🔧 python run.py --setup - Run setup wizard again")
    print("• ⚙️ python run.py --configure - Add/modify services")
    print("• ✅ python run.py --check - Show configuration status")
    print("• ℹ️ python run.py --version - Show version info")
    print("• 📁 python run.py --backup - Create a backup of the current configuration")
    print("• 🔄 python run.py --reset - Reset configuration to default")
    print("• 🔍 python run.py --validate-i18n - Validate translation files")
    print("• ❓ python run.py --help - Show CLI help")

    print(f"\n{Fore.YELLOW}📝 Telegram Chat Commands:{Style.RESET_ALL}")
    print("• 🎬 /movie - Add a movie")
    print("• 📺 /series - Add a TV show")
    print("• 🎵 /music - Add music")
    print("• ❌ /delete - Delete media")
    print("• 📊 /status - Check system status")
    print("• ⚙️ /settings - Manage settings")
    print("• ❓ /help - Show help message")

    print(f"\n{Fore.YELLOW}📚 Resources:{Style.RESET_ALL}")
    print(f"• 🌐 Repository: {Fore.CYAN}https://github.com/cyneric/addarr{Style.RESET_ALL}")
    print(f"• 📖 Documentation: {Fore.CYAN}https://github.com/cyneric/addarr/wiki{Style.RESET_ALL}")
    print(f"• 🐛 Issues: {Fore.CYAN}https://github.com/cyneric/addarr/issues{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}🚀 Starting bot...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")


def show_token_help():
    """Show help information for Telegram bot token configuration"""
    print(f"\n{Fore.RED}❌ Invalid Telegram Bot Token!")
    print(f"\n{Fore.YELLOW}How to fix this:")
    print("1. Get a valid token from @BotFather on Telegram:")
    print("   • Open Telegram and search for @BotFather")
    print("   • Send /newbot to create a new bot")
    print("   • Follow the instructions to get your token")
    print("\n2. Update your config.yaml:")
    print("   • Open config.yaml in a text editor")
    print("   • Find the 'telegram' section")
    print("   • Update the token value")
    print("\nExample config.yaml:")
    print(f"{Fore.CYAN}telegram:")
    print("  token: \"123456789:ABCdefGHIjklMNOpqrsTUVwxyz\"  # Replace with your token")
    print(f"\n{Fore.YELLOW}Or run the setup wizard:")
    print(f"{Fore.CYAN}python run.py --setup")
    print(f"\n{Fore.YELLOW}Need help? Visit: https://github.com/cyneric/addarr/wiki")
