from accessible_output2.outputs.auto import Auto
import application

def output(stuff):
 """Say and braille stuff."""
 return Auto().output(stuff) if application.config.get('accessibility', 'announcements') else None
