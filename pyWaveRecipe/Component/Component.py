from abc import abstractmethod
from io import IOBase, StringIO
import math
from pandas import DataFrame, merge, read_csv, concat
from re import search, findall

MAX_POWERS_HEADER = 'MaxPowers'
FREQUENCY_HEADER = "Frequency (Hz)"
GAIN_HEADER_FORMATER = "S{}{} (dB)"
GAIN_HEADER_PORT_REGEX = "^(?:S(\\d)(\\d) \\(dB\\))$"

class Component:
	@property
	def PortsNumber(self):
		return self.__portsNumber__
	
	__store__:DataFrame = None

	@property
	def SMatrices(self, frequency:float=None, **args) -> DataFrame:
		value = self.__store__
		if frequency:
			value = value.loc[value[FREQUENCY_HEADER] == frequency]
		for arg in args:
			value = value.loc[value[arg[0]] == arg[1]]
		return value
	@SMatrices.setter
	def SMatrices(self, values:DataFrame, **args):
		if args:
			toBeReplacedValues:DataFrame = merge(self.__store__, values, how='inner')
			toBeAddedValues:DataFrame = merge(self.__store__, values, how='outer')
			if not toBeReplacedValues.empty:
				self.__store__.replace(to_replace=args, value=toBeReplacedValues, inplace=True)
			self.__store__ = concat([self.__store__, toBeAddedValues])
		else:
			self.__store__ = values

	@abstractmethod
	def GET_DEPENDENCIES(value:DataFrame) -> list[str]:
		return list(value.filter(regex="^(?!(?:Frequency \(Hz\))|(?:S\d{2} \(dB\))).*$").columns)
	@property
	def Dependancies(self) -> list[str]:
		return Component.GET_DEPENDENCIES(self.__store__)

	@property
	def MaxPowers(self):
		return self.__maxPowers__
	@MaxPowers.setter
	def MaxPowers(self, value):
		if len(value) != self.PortsNumber:
			raise Exception('Max power must be defined for each port')
		self.__maxPowers__ = value

	def __init__(self, portsNumber:int, maxPowers = math.inf):
		self.__portsNumber__ = portsNumber

		sMatrixIndexes:list[tuple[int, int]] = list()
		for inPort in range(1, portsNumber+1):
			for outPort in range(1, portsNumber+1):
				sMatrixIndexes.append((inPort, outPort))
		self.__store__ = DataFrame(data=None, columns=[FREQUENCY_HEADER] + [GAIN_HEADER_FORMATER.format(sMatrixIndex[0], sMatrixIndex[1]) for sMatrixIndex in sMatrixIndexes])

		self.__maxPowers__ = None
		if maxPowers == math.inf:
			maxPowers = [math.inf] * portsNumber
		else:
			if len(maxPowers) != portsNumber:
				raise Exception('Not same max powers as ports number')
			self.MaxPowers = maxPowers

		self.__portsConnections__ = dict(zip(list(range(1, portsNumber + 1)), [list(tuple()) for i in range(0,portsNumber)]))

	@property
	def PortsConnections(self):
		return self.__portsConnections__

	def __connect__(self, selfPort, component, componentPort):
		self.__portsConnections__[selfPort].append((component, componentPort)) # Avoid to use an already used port
		component.__portsConnections__[componentPort].append((self, selfPort))

	def __disconnect__(self, selfPort, component, componentPort):
		self.__portsConnections__[selfPort].remove((component, componentPort))
		component.__portsConnections__[componentPort].remove((self, selfPort))

	def ToCSVStream(self, stream:IOBase) -> None:
		stream.seek(0)
		stream.writelines([f'{MAX_POWERS_HEADER}={self.MaxPowers}\n']) # General metadata printing
		self.__store__.to_csv(stream, index=False, lineterminator='\n')

	def ToCSVString(self) -> str:
		stream = StringIO(newline='\n')
		self.ToCSVStream(stream)
		return stream.getvalue()

	@staticmethod
	def FromCSVStream(io:IOBase):
		match = search(MAX_POWERS_HEADER + '\s*=\s*\[((?:,?\s*(?:[-+]?\d+(?:\.\d+)*(?:[eE][+-]*\d+)?))+)\]', io.readline())
		if match:
			match = findall('(?:,?\s*([-+]?\d+(?:\.\d+)*(?:[eE][+-]*\d+)?)*)', match.group(1))
			maxPowers = [float(m) for m in match[:-1]]
		else:
			maxPowers = math.inf

		dataFrame:DataFrame = read_csv(io)

		columns = dataFrame.filter(regex="^(?:S\\d{2} \\(dB\\))$").columns
		portsNumber = math.nan
		for column in columns:
			portsNumber = max([portsNumber, max([int(indexes) for indexes in list(findall(GAIN_HEADER_PORT_REGEX, column)[0])])])

		math.sqrt(len(dataFrame.filter(regex="^(?:S\\d{2} \\(dB\\))$").columns))
		# if portsNumber % 1 != 0:
		# 	raise Exception("Missing column")
		component = Component(int(portsNumber), maxPowers=maxPowers)
		component.SMatrices = dataFrame

		return component

	@staticmethod
	def FromCSVFile(csvFilePath):
		csvFile = open(csvFilePath)
		component = Component.FromCSVStream(csvFile)
		csvFile.close()
		return component