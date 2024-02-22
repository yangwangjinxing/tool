import subprocess
import os

def run(*cmd):
	# print(cmd)
	return subprocess.run(' '.join(map(str, cmd)).strip().split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def shell(*args, **kwargs):
	args += tuple(f'--{k} {v}' for k,v in kwargs.items() if len(k) > 1 and v is not None)
	args += tuple(f'-{k} {v}' for k,v in kwargs.items() if len(k) == 1 and v is not None)
	return run('adb shell ', *args)

class file:
	@staticmethod
	def rm(path):
		return run('adb rm', path)
	
	@staticmethod
	def ls(path):
		return run('adb ls', path)

	@staticmethod
	def pull(src, dest):
		return run('adb pull', src, dest)

	@staticmethod
	def push(src, dest):
		return run ('adb push', src, dest)

	@staticmethod
	def cat(path):
		return shell('cat', path)


class settings:

	@staticmethod
	def size(x=None, y=None, cache={}):
		xy = ''
		if x and y:
			xy = '%sx%s' % (x, y)
			cache.pop('res', None)
		if cache.get('res'):
			return cache['res']
		cache['res'] = list(map(int, shell('wm size', xy).stdout.strip().split(": ")[-1].split('x')))
		return cache['res']

	@staticmethod
	def show_touches(v):
		shell('settings put system show_touches', v)

	@staticmethod
	def pointer_location(v):
		shell('settings put system pointer_location', v)

class input:
	@staticmethod
	def touch(x, y):
		return shell('input', 'tap', x, y)

	@staticmethod
	def swipe(x1, y1, x2, y2, ms=200):
		return shell('input', 'swipe', x1, y1, x2, y2, ms)
	
	@staticmethod
	def swipe_direct(direct, *args, **kwargs):
		def dircet2xy(direct):
			xy = settings.size()
			dmap = dict(m=0.5,
				L=0, l=0.2, r=0.8, R=1,  #Left & Right
				T=0, t=0.2, b=0.8, B=1,	 #Top & Bottom
				U=0, u=0.2, d=0.8, D=1)  #Up & Down
			for i in range(10):  # 自定义百分比
				dmap[str(i)] = i/10
			return [dmap[d]*xy[i%2] for i, d in enumerate(direct)]
		return input.swipe(*dircet2xy(direct), *args, **kwargs)

	@staticmethod
	def keyevent(event):
		return shell('input', 'keyevent', event)
	
	@staticmethod
	def text(s):
		return shell('input text', s)
	
	@staticmethod
	def wakeup(passwd=None, swipe_up=True):
		res = input.keyevent('KEYCODE_WAKEUP')
		if swipe_up:
			res = res if res.returncode else input.swipe_direct('mdmu')
		if passwd:
			res = res if res.returncode else input.text(passwd)
		return res
	

class am:
	@staticmethod
	def start(**kwargs):
		shell('am start', **kwargs)

def dump(localfile=None, tmpfile='/data/local/tmp/uidump.xml'):
	file.rm(tmpfile)
	shell('uiautomator dump', tmpfile)
	if localfile:
		run('mkdir -p', os.path.dirname(localfile))
		file.pull(tmpfile, localfile)
	xml = file.cat(tmpfile)
	# file.rm(tmpfile)
	return xml

def connect(*ipport):
	cmd = 'adb connect '+ ':'.join(ipport)
	return run(cmd)

def disconnect(*ipport):
	return run('adb disconnect ' + ':'.join(ipport))

def devices():
	return run('abd deevices')