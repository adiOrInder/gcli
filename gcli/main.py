import os
import sys
import argparse
import subprocess
import json

from pathlib import Path
from typing import Optional, Dict, Any
from getpass import getpass
from descope import DeliveryMethod

try:
    from github import Github, GithubException
except ImportError:
    print("❌ PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)

try:
    from descope import DescopeClient
except ImportError:
    print("❌ Descope not installed. Run: pip install descope")
    sys.exit(1)


try:
    import requests
except ImportError:
    print("📦 Installing requests for Ollama support...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    import warnings
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except ImportError:
    pass


class GitHubCLI:
    def __init__(self):
        self.config_dir = Path.home() / '.github-cli'
        self.config_file = self.config_dir / 'config.json'
        self.github = None
        self.descope_client = None
        self.config = {}
        self.ollama_url = "http://localhost:11434"
        self.config_dir.mkdir(exist_ok=True)
        self.load_config()
        
        self.descope_project_id = self.config.get('descope_project_id') 
        self.descope_management_key = self.config.get('descope_management_key')  
        self.init_descope_client()
    
    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    
    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def init_descope_client(self):
        try:
            if not self.descope_project_id or not self.descope_management_key:
                print("⚠️ Descope Project ID or Management Key is missing.")
                print("Please set them using 'gcli config --project-id ...' or environment variables.")
                self.descope_client = None
                return

            self.descope_client = DescopeClient(
                project_id=self.descope_project_id,
                management_key=self.descope_management_key
            )
        except Exception as e:
            print(f"Warning: Could not initialize Descope client: {e}")
            self.descope_client = None
    
    def get_git_diff(self) -> Optional[str]:
        try:
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], capture_output=True)
            if result.returncode == 0:
                result = subprocess.run(['git', 'diff'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
                else:
                    result = subprocess.run(['git', 'diff', 'HEAD~1'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout
            else:
                result = subprocess.run(['git', 'diff', '--staged'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to get git diff: {e}")
            return None
    
    def generate_commit_message(self, git_diff: str) -> Optional[str]:
        try:
            print("🔄 Trying local LLM (Ollama)...")
            result = self.generate_with_ollama(git_diff)
            if result:
                return result
        except Exception as e:
            print(f"⚠️ Local LLM failed: {str(e)[:50]}")
        
        print("🔄 Using intelligent fallback analysis...")
        return self.generate_fallback_message(git_diff)
    
    def check_ollama_running(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> list:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except:
            pass
        return []
    
    def generate_with_ollama(self, git_diff: str) -> Optional[str]:
        try:
            if not self.check_ollama_running():
                print("⚠️ Ollama is not running. Start with 'ollama serve'")
                return None
            
            model = self.config.get('preferred_model', 'llama3.2:1b')
            
            available_models = self.get_available_models()
            if not any(model.startswith(m.split(':')[0]) for m in available_models):
                print(f"⚠️ Model {model} not found. Available models: {', '.join(available_models[:3])}")
                if available_models:
                    model = available_models[0]
                    print(f"🔄 Using {model} instead")
                else:
                    print("❌ No models available. Run 'ollama pull llama3.2:1b' to install a model")
                    return None
            
            prompt = f"""Generate a concise git commit message for the following code changes. 
Use conventional commit format (type: description). 
Types: feat, fix, docs, style, refactor, test, chore.
Keep it under 50 characters.

Code changes:
{git_diff[:1500]}

Commit message:"""

            print(f"🤖 Generating commit message with {model}...")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 50
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']

                if generated_text:
                    for line in generated_text.split('\n'):
                        clean_line = line.strip().strip('"\'`')

                        if ':' in clean_line:
                            commit_type = clean_line.split(':', 1)[0].lower()
                            
                            if commit_type in valid_types and len(clean_line) <= 72:
                                return clean_line

                print("⚠️ Could not find a valid conventional commit message in the LLM output.")
                return None
            
            return None
        except Exception as e:
            print(f"❌ Ollama generation failed: {e}")
            return None
    
    def generate_fallback_message(self, git_diff: str) -> str:
        try:
            diff_lines = git_diff.lower().split('\n')
            
            added_lines = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            removed_lines = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            
            change_types = set()
            
            for line in diff_lines:
                if ('def ' in line or 'class ' in line) and line.startswith('+'):
                    change_types.add('feat')
                elif 'fix' in line or 'bug' in line:
                    change_types.add('fix')
                elif 'import' in line and line.startswith('+'):
                    change_types.add('feat')
                elif 'test' in line:
                    change_types.add('test')
                elif '.md' in git_diff or 'readme' in git_diff.lower():
                    change_types.add('docs')
                elif 'requirements' in git_diff.lower() or 'package' in git_diff.lower():
                    change_types.add('chore')
            
            if 'feat' in change_types:
                commit_type = 'feat'
            elif 'fix' in change_types:
                commit_type = 'fix'
            elif 'test' in change_types:
                commit_type = 'test'
            elif 'docs' in change_types:
                commit_type = 'docs'
            elif 'chore' in change_types:
                commit_type = 'chore'
            else:
                commit_type = 'chore'
            
            if 'openai' in git_diff.lower():
                return "feat: add AI-powered commit message generation"
            elif 'requirements' in git_diff.lower():
                return "chore: update dependencies"
            elif 'main.py' in git_diff and added_lines > 50:
                return "feat: implement major functionality updates"
            elif added_lines > removed_lines * 2:
                return f"{commit_type}: add new features and functionality"
            elif removed_lines > added_lines * 2:
                return f"{commit_type}: remove deprecated code"
            else:
                return f"{commit_type}: update and improve codebase"
        except Exception:
            return "chore: update codebase"
    
    def authenticate_descope(self, email: Optional[str] = None, force: bool = False) -> bool:
        if not self.descope_client:
            print("❌ Descope client not initialized. Please set credentials with 'gcli config'.")
            return False
        if not force and 'descope_session_token' in self.config and 'user_email' in self.config:
            print(f"Already authenticated as: {self.config['user_email']}")
            try:
                session_token = self.config['descope_session_token']
                return self.setup_github_connection()
            except Exception as e:
                print(f"Existing session invalid: {e}")
        if not email:
            email = input("\n📧 Enter your email address: ")
        
        print(f"\n Descope Authentication for {email}")
        print("Choose authentication method:")
        print("1. Magic Link (email)")
        print("2. OTP (email)")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        try:
            if choice == "1":
                return self.authenticate_magic_link(email)
            elif choice == "2":
                return self.authenticate_otp(email)
            else:
                print("❌ Invalid choice")
                return False
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def authenticate_magic_link(self, email: str) -> bool:
        try:
            print("\n📧 Sending magic link...")
            response = self.descope_client.magiclink.sign_in(
                method=DeliveryMethod.EMAIL,
                login_id=email,
                uri="http://localhost:3000/auth/callback"
            )
            
            print(f"✅ Magic link sent to {email}")
            print("Please check your email and click the magic link.")
            print("After clicking the link, you'll be redirected to a page with authentication details.")
            print("\nAfter completing authentication in browser:")
            session_token = input("Paste the session token (or verification code): ").strip()
            
            if session_token:
                return self.complete_authentication(email, session_token)
            else:
                print("❌ No session token provided")
                return False
        except Exception as e:
            print(f"❌ Magic link authentication failed: {e}")
            return False
    
    def authenticate_otp(self, email: str) -> bool:
        try:
            print("\n📱 Sending OTP...")
            response = self.descope_client.otp.sign_in(
                login_id=email,
                method=DeliveryMethod.EMAIL
            )
            
            print(f"✅ OTP sent to {email}")
            otp_code = input("Enter the OTP code: ").strip()
            
            if not otp_code:
                print("❌ No OTP code provided")
                return False
            verify_response = self.descope_client.otp.verify_code(
                method=DeliveryMethod.EMAIL,
                login_id=email,
                code=otp_code
            )
            
            print(f"✅ OTP verification successful!")
            print(f"📋 Full response: {verify_response}")
            if hasattr(verify_response, 'session_jwt') and verify_response.session_jwt:
                session_token = verify_response.session_jwt
                user_info = verify_response.user if hasattr(verify_response, 'user') else None
                return self.complete_authentication_with_session(email, session_token, user_info, verify_response)
            else:
                print("❌ Failed to get session token from response")
                return False
        except Exception as e:
            print(f"❌ OTP authentication failed: {e}")
            return False
    
    def complete_authentication_with_session(self, email: str, session_token: str, user_info: Any, full_response: Any) -> bool:
        try:
            print("\n✅ Descope authentication successful!")
            self.config['descope_session_token'] = session_token
            self.config['user_email'] = email
            github_token = self.extract_github_token_from_session(full_response, user_info)
            
            if github_token:
                print("✅ GitHub token found in Descope session!")
                return self.setup_github_with_token(github_token)
            else:
                print("⚠️  No GitHub token found in session. You may need to configure the GitHub OAuth integration in Descope.")
                print("Falling back to manual GitHub token input...")
                return self.setup_github_connection()
        except Exception as e:
            print(f"❌ Failed to complete authentication: {e}")
            return False
    
    def extract_github_token_from_session(self, full_response: Any, user_info: Any) -> Optional[str]:
        try:
            github_token = None
            if user_info:
                print(f"📋 User info: {user_info}")
                if hasattr(user_info, 'custom_attributes') and user_info.custom_attributes:
                    custom_attrs = user_info.custom_attributes
                    print(f"📋 Custom attributes: {custom_attrs}")
                    if 'github_token' in custom_attrs:
                        github_token = custom_attrs['github_token']
                    elif 'oauth_tokens' in custom_attrs:
                        oauth_tokens = custom_attrs['oauth_tokens']
                        if isinstance(oauth_tokens, dict) and 'github' in oauth_tokens:
                            github_token = oauth_tokens['github'].get('access_token')
                if hasattr(user_info, 'oauth') and user_info.oauth:
                    print(f"📋 OAuth info: {user_info.oauth}")
                    for provider_name, provider_data in user_info.oauth.items():
                        if provider_name.lower() == 'github':
                            if isinstance(provider_data, dict) and 'access_token' in provider_data:
                                github_token = provider_data['access_token']
            if not github_token and full_response:
                print(f"📋 Checking full response for GitHub token...")
                if hasattr(full_response, 'oauth_tokens') and full_response.oauth_tokens:
                    oauth_tokens = full_response.oauth_tokens
                    print(f"📋 OAuth tokens: {oauth_tokens}")
                    if isinstance(oauth_tokens, dict) and 'github' in oauth_tokens:
                        github_data = oauth_tokens['github']
                        if isinstance(github_data, dict) and 'access_token' in github_data:
                            github_token = github_data['access_token']
                if not github_token and hasattr(full_response, 'user') and full_response.user:
                    user = full_response.user
                    if hasattr(user, 'oauth') and user.oauth:
                        for provider_name, provider_data in user.oauth.items():
                            if provider_name.lower() == 'github':
                                if isinstance(provider_data, dict) and 'access_token' in provider_data:
                                    github_token = provider_data['access_token']
            
            if github_token:
                print(f"✅ Found GitHub token in Descope session!")
                return github_token
            else:
                print("⚠️  No GitHub token found in session data")
                return None
        except Exception as e:
            print(f"⚠️  Error extracting GitHub token from session: {e}")
            return None
    
    def setup_github_with_token(self, github_token: str) -> bool:
        try:
            self.github = Github(github_token)
            user = self.github.get_user()
            self.config['github_token'] = github_token
            self.config['github_username'] = user.login
            self.save_config()
            
            print(f"✅ GitHub automatically connected as: {user.login}")
            return True
        except GithubException as e:
            print(f"❌ Failed to connect to GitHub with extracted token: {e}")
            print("Falling back to manual token input...")
            return self.setup_github_connection()
        except Exception as e:
            print(f"❌ Unexpected error connecting to GitHub: {e}")
            return False
    
    def complete_authentication(self, email: str, session_token: str) -> bool:
        try:
            print("\n✅ Descope authentication successful!")
            self.config['descope_session_token'] = session_token
            self.config['user_email'] = email
            print("⚠️  Magic link authentication completed, but no session data available for GitHub token extraction.")
            print("Please provide your GitHub token manually...")
            return self.setup_github_connection()
        except Exception as e:
            print(f"❌ Failed to complete authentication: {e}")
            return False
    
    def setup_github_connection(self) -> bool:
        if 'github_token' in self.config and 'github_username' in self.config:
            try:
                self.github = Github(self.config['github_token'])
                user = self.github.get_user()
                print(f"🐙 GitHub connected as: {user.login}")
                return True
            except GithubException:
                print("⚠️  Existing GitHub token invalid, requesting new one")
        
        print("\n🐙 GitHub Token Setup")
        print("You need a GitHub Personal Access Token for repository operations.")
        print("Create one at: https://github.com/settings/tokens")
        print("Required scopes: repo, user")
        
        github_token = getpass("Enter your GitHub token: ").strip()
        
        if not github_token:
            print("❌ No GitHub token provided")
            return False
        
        try:
            self.github = Github(github_token)
            user = self.github.get_user()
            self.config['github_token'] = github_token
            self.config['github_username'] = user.login
            self.save_config()
            
            print(f"✅ GitHub connected as: {user.login}")
            return True
        except GithubException as e:
            print(f"❌ GitHub authentication failed: {e}")
            return False
    
    def authenticate(self, email: Optional[str] = None, force: bool = False) -> bool:
        return self.authenticate_descope(email, force)
    
    def get_or_create_repo(self, repo_name: str, description: str = "", private: bool = False) -> Optional[Any]:
        try:
            user = self.github.get_user()
            repo = user.get_repo(repo_name)
            print(f"📁 Found existing repository: {repo.full_name}")
            return repo
        except GithubException:
            try:
                user = self.github.get_user()
                repo = user.create_repo(
                    name=repo_name,
                    description=description,
                    private=private,
                    auto_init=True
                )
                print(f"🆕 Created new repository: {repo.full_name}")
                return repo
            except GithubException as e:
                print(f"❌ Failed to create repository: {e}")
                return None
    
    def init_local_repo(self, repo_url: str) -> bool:
        try:
            result = subprocess.run(['git', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                print("📁 Directory is already a git repository")
                result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
                if result.returncode != 0:
                    subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
                    print(f"🔗 Added remote origin: {repo_url}")
            else:
                subprocess.run(['git', 'init'], check=True)
                subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
                print(f"🆕 Initialized git repository with origin: {repo_url}")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False
    
    def commit_and_push(self, message: str, branch: str = 'main') -> bool:
        try:
            subprocess.run(['git', 'add', '.'], check=True)
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], capture_output=True)
            if result.returncode == 0:
                print("ℹ️  No changes to commit")
                return True
            subprocess.run(['git', 'commit', '-m', message], check=True)
            print(f"✅ Committed changes: {message}")
            current_branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True, check=True)
            current_branch = current_branch_result.stdout.strip()
            subprocess.run(['git', 'push', 'origin', current_branch], check=True)
            branch = current_branch
            print(f"🚀 Pushed to {branch} branch")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False

    def set_descope_config(self, project_id: Optional[str] = None, management_key: Optional[str] = None) -> bool:
        if not project_id and not management_key:
            print("❌ You must provide either a project ID or a management key.")
            return False
        
        if project_id:
            self.config['descope_project_id'] = project_id
            print(f"✅ Descope Project ID set to: {project_id}")
        
        if management_key:
            self.config['descope_management_key'] = management_key
            print("✅ Descope Management Key has been set.")
            
        self.save_config()
        print("\n🔧 Configuration saved. The new settings will be used on the next run.")
        return True

    def set_origin(self, repo_url: str) -> bool:
        try:
            check_git = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
            if check_git.returncode != 0 or not check_git.stdout.strip() == 'true':
                print("❌ This is not a git repository. Run 'gcli init <repo-name>' first.")
                return False

            check_remote = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
            if check_remote.returncode == 0:
                subprocess.run(['git', 'remote', 'set-url', 'origin', repo_url], check=True)
                print(f"✅ Updated remote origin to: {repo_url}")
            else:
                subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
                print(f"✅ Set remote origin to: {repo_url}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to set remote origin: {e}")
            return False
    
    def show_issues(self, limit: int, repo: str, label: list) -> None:
        try:
            issues = self.github.get_repo(repo).get_issues(labels=label)
            count = 0
            for issue in issues:
                if count >= limit:
                    break
                print(f"#{issue.number}: {issue.title}")
                print(f"  - Opened by: {issue.user.login}")
                print(f"  - URL: {issue.html_url}\n")
                count += 1
        except GithubException as e:
            print(f"❌ An error occurred: {e}")
            print("Please check your GITHUB_TOKEN and REPO_NAME.")
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
            
    def show_status(self):
        print("\n📊 Status:")
        if 'user_email' in self.config:
            print(f"🔐 Descope: Authenticated as {self.config['user_email']}")
        else:
            print("🔐 Descope: Not authenticated")
        if 'github_username' in self.config:
            print(f"🐙 GitHub: Connected as {self.config['github_username']}")
        else:
            print("🐙 GitHub: Not connected")
        
        if self.check_ollama_running():
            models = self.get_available_models()
            preferred = self.config.get('preferred_model', 'None')
            print(f"🤖 Ollama: Running ({len(models)} models available)")
            print(f"🎯 Preferred model: {preferred}")
        else:
            print("🤖 Ollama: Not running (install from https://ollama.ai)")
        
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if result.returncode == 0:
                if result.stdout.strip():
                    print(f"📝 Git: {len(result.stdout.strip().split())} uncommitted files")
                else:
                    print("✅ Git: Working directory clean")
        except subprocess.CalledProcessError:
            print("📁 Not in a git repository")
        
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"🔗 Remote origin: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            print("🔗 No remote origin set")

def main():
    parser = argparse.ArgumentParser(
        description='A CLI for GitHub with AI-powered commits.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gcli auth
  gcli config --project-id "YOUR_ID" --management-key "YOUR_KEY"
  gcli init my-awesome-repo --description "My new project"
  gcli set-origin https://github.com/user/repo.git
  gcli commit --auto
  gcli status
  gcli issue PyGithub/PyGithub --limit 5
        """
    ) 
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)
    auth_parser = subparsers.add_parser('auth', help='Authenticate with Descope and GitHub')
    auth_parser.add_argument('--email', help='Email address for Descope authentication')
    auth_parser.add_argument('--force', action='store_true', help='Force re-authentication')

    config_parser = subparsers.add_parser('config', help='Set configuration values for Descope')
    config_parser.add_argument('--project-id', dest='project_id', help='Your Descope Project ID')
    config_parser.add_argument('--management-key', dest='management_key', help='Your Descope Management Key')

    issue_parser = subparsers.add_parser('issue', help='Show repository issues')
    issue_parser.add_argument('repo_name', help='Repository name (e.g., "owner/repo")')
    issue_parser.add_argument('--limit', type=int, default=10, help='Number of issues to show (default: 10)')
    issue_parser.add_argument('--label', action='append', help='Filter by label (can be used multiple times)')
    
    init_parser = subparsers.add_parser('init', help='Initialize a local and remote repository')
    init_parser.add_argument('repo_name', help='Name for the new repository')
    init_parser.add_argument('--description', default='', help='Repository description')
    init_parser.add_argument('--private', action='store_true', help='Create a private repository')

    origin_parser = subparsers.add_parser('set-origin', help='Set or update the remote origin for the current repository')
    origin_parser.add_argument('repo_url', help='The full URL of the remote repository')
    
    commit_parser = subparsers.add_parser('commit', help='Commit and push changes with an optional auto-generated message')
    commit_parser.add_argument('message', nargs='?', help='Commit message (optional if using --auto)')
    commit_parser.add_argument('--auto', action='store_true', help='Generate commit message automatically using local AI')
    commit_parser.add_argument('--branch', default='main', help='Branch to push to (default: main)')
    
    status_parser = subparsers.add_parser('status', help='Show current authentication and repository status')
    args = parser.parse_args()
    cli = GitHubCLI()
    if args.command == 'auth':
        if not cli.authenticate(args.email, args.force):
            sys.exit(1)

    elif args.command == 'config':
        if not cli.set_descope_config(project_id=args.project_id, management_key=args.management_key):
            sys.exit(1)
    
    elif args.command == 'init':
        if not cli.authenticate():
            print("❌ Authentication required for repository operations. Run 'gcli auth'.")
            sys.exit(1)
        repo = cli.get_or_create_repo(args.repo_name, args.description, args.private)
        if not repo:
            sys.exit(1)
        if not cli.init_local_repo(repo.clone_url):
            sys.exit(1)
            
    elif args.command == 'set-origin':
        if not cli.set_origin(args.repo_url):
            sys.exit(1)
    
    elif args.command == 'commit':
        if not cli.authenticate():
            print("❌ Authentication required for git operations. Run 'gcli auth'.")
            sys.exit(1)
        
        message = args.message
        
        if args.auto:
            print("🤖 Generating commit message automatically...")
            git_diff = cli.get_git_diff()
            if not git_diff:
                print("✅ No changes detected to commit.")
                sys.exit(0)
            
            generated_message = cli.generate_commit_message(git_diff)
            if not generated_message:
                print("❌ Failed to generate commit message")
                sys.exit(1)
            
            print(f"\n🎆 Generated commit message: {generated_message}")
            
            confirm = input("Use this commit message? (y/n/edit): ").strip().lower()
            if confirm == 'n':
                print("❌ Commit cancelled")
                sys.exit(1)
            elif confirm == 'edit':
                message = input(f"Edit message [{generated_message}]: ").strip()
                if not message:
                    message = generated_message
            else:
                message = generated_message
        
        elif not message:
            print("❌ Commit message is required when not using --auto. Or, use --auto to generate one.")
            commit_parser.print_help()
            sys.exit(1)
        
        if not cli.commit_and_push(message, args.branch):
            sys.exit(1)
    
    elif args.command == 'status':
        cli.show_status()
    
    elif args.command == 'issue':
        if not cli.authenticate():
            print("❌ Authentication required for repository operations. Run 'gcli auth'.")
            sys.exit(1)
        labels = args.label if args.label else []
        cli.show_issues(args.limit, args.repo_name, labels)

if __name__ == '__main__':
    main()

