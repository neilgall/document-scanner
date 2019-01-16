#!/usr/bin/env python
from enum import Enum
from PIL import Image
import argparse
import inotify.adapters
import os
import pytesseract
import shutil
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
		#print(event,path)

class JPEGHandler:
	"""Handler for the creation of a new JPEG"""
	def __init__(self, destination):
		self._destination = destination

	def __call__(self, path):
		print(f"Processing {path}")
		try:
			base = os.path.basename(path)
			dest_jpg = os.path.join(self._destination, base)
			dest_pdf = os.path.splitext(dest_jpg)[0] + ".pdf"
			pdf = pytesseract.image_to_pdf_or_hocr(Image.open(path), extension='pdf')
			with open(dest_pdf, 'wb') as f:
				f.write(pdf)
			shutil.move(path, dest_jpg)
		except Exception as e:
			print(e)


def is_jpg(path):
	"""Determine if a file path is a JPEG"""
	ext = os.path.splitext(path)[1]
	return ext.lower() in [".jpg", ".jpeg"]

def watch(folder, handler):
	"""
	Watch 'folder' for file system events, passing them to 'handler'
	"""
	i = inotify.adapters.Inotify()
	i.add_watch(folder)
	for (_, types, path, filename) in i.event_gen(yield_nones=False):
		handler(types, os.path.join(path, filename))

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("inbox", help="Folder to watch for new images")
	parser.add_argument("outbox", help="Folder for processed images")
	args = parser.parse_args()

	print(f"Watching {args.inbox} for files; sending results to {args.outbox}")

	handler = FileHandler(is_jpg, JPEGHandler(args.outbox))
	watch(args.inbox, handler)
