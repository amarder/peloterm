"""Strava API integration for uploading rides."""

import os
import json
import time
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


class StravaConfig:
    """Manage Strava API configuration and tokens."""
    
    def __init__(self):
        """Initialize Strava configuration."""
        self.config_dir = Path.home() / ".peloterm"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "strava_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Strava configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _save_config(self) -> None:
        """Save Strava configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            console.print(f"[red]Error saving Strava config: {e}[/red]")
    
    def setup_credentials(self) -> bool:
        """Set up Strava API credentials through interactive prompts."""
        console.print(Panel.fit(
            "[bold blue]Strava API Setup[/bold blue]\n\n"
            "To upload rides to Strava, you need to create a Strava API application:\n\n"
            "1. Go to https://www.strava.com/settings/api\n"
            "2. Create a new application\n"
            "3. Set Authorization Callback Domain to: localhost\n"
            "4. Note your Client ID and Client Secret\n",
            title="📡 Strava Setup"
        ))
        
        if not Confirm.ask("Have you created a Strava API application?"):
            console.print("[yellow]Please create a Strava API application first.[/yellow]")
            return False
        
        client_id = Prompt.ask("Enter your Strava Client ID")
        client_secret = Prompt.ask("Enter your Strava Client Secret", password=True)
        
        if not client_id or not client_secret:
            console.print("[red]Client ID and Client Secret are required.[/red]")
            return False
        
        self.config.update({
            'client_id': client_id,
            'client_secret': client_secret
        })
        self._save_config()
        
        console.print("[green]✓ Strava credentials saved successfully![/green]")
        return True
    
    def get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        if not self.has_credentials():
            return None
        
        # Check if we have a valid access token
        if 'access_token' in self.config and 'expires_at' in self.config:
            if time.time() < self.config['expires_at']:
                return self.config['access_token']
        
        # Try to refresh the token
        if 'refresh_token' in self.config:
            return self._refresh_access_token()
        
        # Need to do initial authorization
        return self._authorize()
    
    def has_credentials(self) -> bool:
        """Check if we have the required credentials."""
        return 'client_id' in self.config and 'client_secret' in self.config
    
    def _authorize(self) -> Optional[str]:
        """Perform initial OAuth authorization."""
        console.print(Panel.fit(
            "[bold blue]Strava Authorization Required[/bold blue]\n\n"
            "I'll open your web browser to authorize Peloterm with Strava.\n"
            "After authorization, you'll get a code to enter here.\n",
            title="🔐 Authorization"
        ))
        
        if not Confirm.ask("Continue with authorization?"):
            return None
        
        # Build authorization URL
        auth_url = (
            f"https://www.strava.com/oauth/authorize?"
            f"client_id={self.config['client_id']}&"
            f"response_type=code&"
            f"redirect_uri=http://localhost:8080&"
            f"approval_prompt=force&"
            f"scope=activity:write"
        )
        
        console.print(f"[blue]Opening browser to: {auth_url}[/blue]")
        webbrowser.open(auth_url)
        
        console.print("\n[yellow]After authorizing, you'll be redirected to a page that won't load.[/yellow]")
        console.print("[yellow]Copy the 'code' parameter from the URL and paste it here.[/yellow]")
        console.print("[dim]URL will look like: http://localhost:8080/?state=&code=YOUR_CODE_HERE&scope=read,activity:write[/dim]\n")
        
        auth_code = Prompt.ask("Enter the authorization code")
        
        if not auth_code:
            console.print("[red]Authorization code is required.[/red]")
            return None
        
        # Exchange code for token
        token_data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'code': auth_code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post('https://www.strava.com/oauth/token', data=token_data)
            response.raise_for_status()
            
            token_info = response.json()
            
            self.config.update({
                'access_token': token_info['access_token'],
                'refresh_token': token_info['refresh_token'],
                'expires_at': token_info['expires_at']
            })
            self._save_config()
            
            console.print("[green]✓ Successfully authorized with Strava![/green]")
            return token_info['access_token']
            
        except requests.RequestException as e:
            console.print(f"[red]Error getting access token: {e}[/red]")
            return None
    
    def _refresh_access_token(self) -> Optional[str]:
        """Refresh the access token using the refresh token."""
        token_data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'refresh_token': self.config['refresh_token'],
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post('https://www.strava.com/oauth/token', data=token_data)
            response.raise_for_status()
            
            token_info = response.json()
            
            self.config.update({
                'access_token': token_info['access_token'],
                'refresh_token': token_info['refresh_token'],
                'expires_at': token_info['expires_at']
            })
            self._save_config()
            
            return token_info['access_token']
            
        except requests.RequestException as e:
            console.print(f"[red]Error refreshing access token: {e}[/red]")
            return None


class StravaUploader:
    """Handle uploading rides to Strava."""
    
    def __init__(self):
        """Initialize the Strava uploader."""
        self.config = StravaConfig()
    
    def setup(self) -> bool:
        """Set up Strava integration."""
        if not self.config.has_credentials():
            return self.config.setup_credentials()
        return True
    
    def upload_ride(self, fit_file_path: str, name: Optional[str] = None, 
                   description: Optional[str] = None, activity_type: str = "Ride") -> bool:
        """Upload a FIT file to Strava.
        
        Args:
            fit_file_path: Path to the FIT file to upload
            name: Optional name for the activity
            description: Optional description for the activity  
            activity_type: Type of activity (default: "Ride")
            
        Returns:
            True if upload was successful, False otherwise
        """
        access_token = self.config.get_access_token()
        if not access_token:
            console.print("[red]No valid Strava access token. Run setup first.[/red]")
            return False
        
        fit_path = Path(fit_file_path)
        if not fit_path.exists():
            console.print(f"[red]FIT file not found: {fit_file_path}[/red]")
            return False
        
        # Check file size (Strava limit is 25MB)
        file_size = fit_path.stat().st_size
        if file_size > 25 * 1024 * 1024:  # 25MB in bytes
            console.print(f"[red]File too large: {file_size / (1024*1024):.1f}MB (max 25MB)[/red]")
            return False
        
        console.print(f"[blue]Uploading {fit_path.name} to Strava ({file_size / 1024:.1f}KB)...[/blue]")
        
        # Prepare upload data
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        files = {
            'file': (fit_path.name, open(fit_path, 'rb'), 'application/octet-stream')
        }
        
        data = {
            'data_type': 'fit',
            'activity_type': activity_type
        }
        
        if name:
            data['name'] = name
        if description:
            data['description'] = description
        
        try:
            response = requests.post(
                'https://www.strava.com/api/v3/uploads',
                headers=headers,
                files=files,
                data=data
            )
            files['file'][1].close()  # Close the file
            
            response.raise_for_status()
            upload_result = response.json()
            
            upload_id = upload_result.get('id')
            if upload_id:
                console.print(f"[green]✓ Upload initiated! Upload ID: {upload_id}[/green]")
                
                # Check upload status
                status = self._check_upload_status(upload_id, access_token)
                if status:
                    console.print(f"[green]🎉 Successfully uploaded to Strava![/green]")
                    if 'activity_id' in status:
                        activity_url = f"https://www.strava.com/activities/{status['activity_id']}"
                        console.print(f"[blue]🔗 View your activity: {activity_url}[/blue]")
                return True
            else:
                console.print(f"[yellow]Upload response: {upload_result}[/yellow]")
                return False
                
        except requests.RequestException as e:
            console.print(f"[red]Error uploading to Strava: {e}[/red]")
            return False
    
    def _check_upload_status(self, upload_id: int, access_token: str, max_attempts: int = 10) -> Optional[Dict]:
        """Check the status of an upload."""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f'https://www.strava.com/api/v3/uploads/{upload_id}',
                    headers=headers
                )
                response.raise_for_status()
                
                status = response.json()
                
                if status['status'] == 'Your activity is ready.':
                    return status
                elif status['status'] == 'There was an error processing your activity.':
                    console.print(f"[red]Error processing upload: {status.get('error', 'Unknown error')}[/red]")
                    return None
                else:
                    console.print(f"[dim]Upload status: {status['status']}[/dim]")
                    time.sleep(2)  # Wait before checking again
                    
            except requests.RequestException as e:
                console.print(f"[yellow]Error checking upload status: {e}[/yellow]")
                time.sleep(2)
        
        console.print("[yellow]Upload status check timed out[/yellow]")
        return None
    
    def test_connection(self) -> bool:
        """Test the Strava API connection."""
        access_token = self.config.get_access_token()
        if not access_token:
            console.print("[red]No valid Strava access token.[/red]")
            return False
        
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        try:
            response = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)
            response.raise_for_status()
            
            athlete = response.json()
            console.print(f"[green]✓ Connected to Strava as {athlete.get('firstname', '')} {athlete.get('lastname', '')}[/green]")
            return True
            
        except requests.RequestException as e:
            console.print(f"[red]Error connecting to Strava: {e}[/red]")
            return False 