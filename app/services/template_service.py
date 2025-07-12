import configparser
from typing import Dict, Any, List
from pathlib import Path


class TemplateService:
    def __init__(self):
        self.template_path = Path("templates/activity_prompt.ini")
        self._load_template()
    
    def _load_template(self):
        """Load the activity prompt template"""
        if not self.template_path.exists():
            self._create_default_template()
        
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(self.template_path)
    
    def _create_default_template(self):
        """Create the default activity prompt template"""
        self.template_path.parent.mkdir(exist_ok=True)
        
        template_content = """[base_prompt]
system_role = You are an expert children's activity coordinator at a space-themed summer academy
target_audience = 8-year-old children with developing fine motor skills and creativity
confidence_level = You must have 95 percent confidence this activity is safe and appropriate

[activity_framework]
create_instruction = Create a fun {selected_category} activity that takes approximately {selected_duration} minutes
materials_instruction = Use at least {min_materials_count} of these available materials: {selected_materials}
learning_focus = The activity should help develop: {selected_objectives}
theme_integration = Incorporate a galactic space academy theme naturally into the activity

[output_structure]
title_requirement = Provide an exciting space-themed title
overview_requirement = Give a brief description of what the child will create and why it's cool
steps_requirement = Break down into clear, numbered steps using simple 8-year-old friendly language
time_guidance = Suggest rough time allocation for each major step
encouragement = Include positive, encouraging language throughout

[safety_and_quality]
safety_check = Ensure all steps are safe for 8-year-olds working with the specified materials
age_appropriateness = Verify fine motor skills required match 8-year-old capabilities
completion_confidence = Child should feel proud and accomplished when finished

[uniqueness_requirement]
avoid_repetition = Do NOT create activities similar to these recent activities: {recent_activities_summary}
ensure_variety = Make this activity distinctly different in approach, final product, and techniques used
"""
        
        with open(self.template_path, 'w') as f:
            f.write(template_content)
    
    def populate_template(self, variables: Dict[str, Any]) -> str:
        """
        Populate the template with the given variables
        """
        prompt_parts = []
        
        # Add base prompt section
        prompt_parts.append(f"System Role: {self.config['base_prompt']['system_role']}")
        prompt_parts.append(f"Target Audience: {self.config['base_prompt']['target_audience']}")
        prompt_parts.append(f"Confidence Level: {self.config['base_prompt']['confidence_level']}")
        prompt_parts.append("")
        
        # Add activity framework
        create_instruction = self.config['activity_framework']['create_instruction'].format(**variables)
        materials_instruction = self.config['activity_framework']['materials_instruction'].format(**variables)
        learning_focus = self.config['activity_framework']['learning_focus'].format(**variables)
        theme_integration = self.config['activity_framework']['theme_integration']
        
        prompt_parts.append("ACTIVITY REQUIREMENTS:")
        prompt_parts.append(f"- {create_instruction}")
        prompt_parts.append(f"- {materials_instruction}")
        prompt_parts.append(f"- {learning_focus}")
        prompt_parts.append(f"- {theme_integration}")
        prompt_parts.append("")
        
        # Add output structure
        prompt_parts.append("OUTPUT FORMAT:")
        for key, value in self.config['output_structure'].items():
            prompt_parts.append(f"- {value}")
        prompt_parts.append("")
        
        # Add safety and quality
        prompt_parts.append("SAFETY AND QUALITY:")
        for key, value in self.config['safety_and_quality'].items():
            prompt_parts.append(f"- {value}")
        prompt_parts.append("")
        
        # Add uniqueness requirements
        avoid_repetition = self.config['uniqueness_requirement']['avoid_repetition'].format(**variables)
        ensure_variety = self.config['uniqueness_requirement']['ensure_variety']
        
        prompt_parts.append("UNIQUENESS REQUIREMENTS:")
        prompt_parts.append(f"- {avoid_repetition}")
        prompt_parts.append(f"- {ensure_variety}")
        prompt_parts.append("")
        
        prompt_parts.append("Please generate a complete activity following all the above requirements.")
        
        return "\n".join(prompt_parts)
    
    def format_materials_list(self, materials: List[str]) -> str:
        """Format materials list for template"""
        return ", ".join(materials)
    
    def format_objectives_list(self, objectives: List[str]) -> str:
        """Format objectives list for template"""
        return ", ".join(objectives) 