import yaml
from pathlib import Path

# Load prompts from YAML file
def load_yaml(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        # safe_load ensures that the YAML is loaded as a Python dictionary
        # lode method may excute embedded code
        return yaml.safe_load(f)
    
project_root = Path(__file__).parent.parent
yml_path = project_root / "prompt" / "prompts.yml"

prompt_yml_content = load_yaml(yml_path)
print(f"prompt_yml_content: {prompt_yml_content}")

# main_agent content
main_agent_content = prompt_yml_content["main_agent"]

# sub_agents content
sub_agents_content = prompt_yml_content["sub_agents"]

print(f"main_agent: {main_agent_content}")
print(f"sub_agents: {sub_agents_content}")