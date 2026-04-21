import yaml

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    print('Config loaded successfully')
    print('LLM config keys:', list(config['llm'].keys()))
    print('High level model:', config['llm']['high']['model'])
    print('Medium level model:', config['llm']['medium']['model'])
    print('Low level model:', config['llm']['low']['model'])