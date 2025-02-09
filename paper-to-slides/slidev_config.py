class SlidevConfigurator:
    def generate_config(self, theme="seriph", features=None):
        """Generate slidev config with auto-play and drawings"""
        base_config = {
            "theme": theme,
            "remoteAssets": False,
            "drawings": {
                "persist": False,
                "enabled": True
            },
            "features": {
                "audio": True,
                "autoPlay": {
                    "enabled": True,
                    "interval": 60000
                }
            }
        }
        
        if features:
            base_config["features"].update(features)
            
        return base_config
    
    def inject_theme(self, slides_md, config):
        """Prepend config to markdown output"""
        config_yaml = yaml.safe_dump(config)
        return f"---\n{config_yaml}\n---\n\n{slides_md}"

    def _add_transition_controls(self, config):
        """Add advanced transition settings"""
        config["transition"] = {
            "enable_background": True,
            "enable_controls": True,
            "progress_bar": True
        }
        return config 