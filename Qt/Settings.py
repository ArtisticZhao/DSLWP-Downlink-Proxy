# coding: utf-8
"""
Save and load setting from UI
"""
class Settings:
    def __init__(self, ui) -> None:
        self.ui = ui
        self.all_ui =  [attr for attr in dir(ui) if not callable(getattr(ui, attr)) and not attr.startswith("__")]
        

    def save_settings(self):
        obj = self._find_obj_by_name("name_text")
        print(obj.objectName())
        doc = dict()

        doc['nickname'] = str(self.ui.name_text.text())

    def _find_obj_by_name(self, kw):
        for each in self.all_ui:
            value = getattr(self.ui, each, None)
            if value is not None:
                if value.objectName() == kw:
                    return value
        return None