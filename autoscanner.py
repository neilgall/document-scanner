#!/usr/bin/env python
from enum import Enum
import inotify.adapters
import os
import sys

class FileState(Enum):
	CREATED = 1
	MODIFIED = 2
	CLOSED = 3

class FileHandler:
	"""
	Event handler which maintains a state machine for each path
	seen. When a file goes through the create, write, close sequence,
	notifies the created handler.
	"""
	def __init__(self, filter, created_handler):
		self._files = {}
		self._filter = filter
		self._created_handler = created_handler

	def __call__(self, event, path):
		if ('IN_CREATE' in event or 'IN_OPEN' in event) and self._filter(path):
			self._files[path] = FileState.CREATED
		elif 'IN_MODIFY' in event and self._files.get(path) == FileState.CREATED:
			self._files[path] = FileState.MODIFIED
		elif 'IN_CLOSE_WRITE' in event or 'IN_CLOSE_NOWRITE' in event:
			if self._files.get(path) == FileState.MODIFIED:
				self._created_handler(path)
			if path in self._files:
				del self._files[path]

def is_jpg(path):
	"""Determine if a file path is a JPEG"""
	(_, ext) = os.path.splitext(path)
	return ext.lower() in [".jpg", ".jpeg"]

def on_create_jpeg(path):
	"""Handler for the creation of a new JPEG"""
	print(path)

def watch(folder, handler):
	"""
	Watch 'folder' for file system events, passing them to 'handler'
	"""
	i = inotify.adapters.Inotify()
	i.add_watch(folder)
	for (_, types, path, filename) in i.event_gen(yield_nones=False):
		handler(types, os.path.join(path, filename))

if __name__ == "__main__":
	folder = os.getcwd() if len(sys.argv) < 2 else sys.argv[1]
	watch(folder, FileHandler(is_jpg, on_create_jpeg))
