import json
from datetime import datetime

class Hook:
    def __init__(self, hook_id, **kwargs):
        self.id = hook_id
        self.type = kwargs.get('type')
        self.name = kwargs.get('name')
        self.url = kwargs.get('url')
        self.queues = kwargs.get('queues')
        self.run_after = kwargs.get('run_after')
        self.active = kwargs.get('active')
        self.events = kwargs.get('events')
        self.sideload = kwargs.get('sideload')
        self.metadata = kwargs.get('metadata')
        self.config = kwargs.get('config')
        self.token_owner = kwargs.get('token_owner')
        self.token_lifetime_s = kwargs.get('token_lifetime_s')
        self.test = kwargs.get('test')
        self.description = kwargs.get('description')
        self.extension_source = kwargs.get('extension_source')
        self.settings = kwargs.get('settings')
        self.settings_schema = kwargs.get('settings_schema')
        self.secrets = kwargs.get('secrets')
        self.guide = kwargs.get('guide')
        self.read_more_url = kwargs.get('read_more_url')
        self.extension_image_url = kwargs.get('extension_image_url')
        self.hook_template = kwargs.get('hook_template')
        self.modified_by = kwargs.get('modified_by')
        self.modified_at = kwargs.get('modified_at', datetime.now().isoformat())
    
    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'Hook' object has no attribute '{name}'")

class HookManager:
    def __init__(self):
        self.hooks = {}

    def add_hook(self, hook_data:dict):
        hook_id = str(hook_data.get('id'))
        if hook_id in self.hooks:
            raise ValueError(f"Hook with ID {hook_id} already exists")
        hook = Hook(hook_id, **hook_data)
        self.hooks[hook_id] = hook

    def remove_hook(self, hook_id:str):
        if hook_id in self.hooks:
            del self.hooks[hook_id]
        else:
            raise ValueError(f"Hook with ID {hook_id} not found")

    def get_hook(self, hook_id:str):
        return self.hooks.get(hook_id)

    # def load_hook_from_json(self, json_data):
    #     hook_data = json.loads(json_data)
    #     hook_id = hook_data.get('id')
    #     self._add_hook(hook_id, hook_data)

    