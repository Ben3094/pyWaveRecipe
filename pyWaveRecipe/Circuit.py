from .Component import Component, FREQUENCY_HEADER
from networkx import Graph, connected_components, shortest_path
from numpy import any, isnan
from pandas import concat

COMPONENT_PROPERTY_NAME = 'Component'
PORT_CONNECTION_PROPERTY_NAME = 'PortsConnection'

class Circuit(Graph):
	def __init__(self, **attr):
		self.__updated__ = False
		self.__freePorts__ = list()
		super().__init__(incoming_graph_data=None, **attr)

	@property
	def Components(self) -> dict[object, Component]:
		return dict([(node, self.nodes[node][COMPONENT_PROPERTY_NAME]) for node in self.nodes])

	def add_node(self, node_for_adding, component, **attr):
		self.__updated__ = True
		super().add_node(node_for_adding, **attr)
		self.nodes[node_for_adding][COMPONENT_PROPERTY_NAME] = component

	def remove_node(self, n):
		self.__updated__ = False
		if n in self.nodes:
			for (component, componentPort) in self.nodes[n][COMPONENT_PROPERTY_NAME].PortsConnections:
				self.nodes[n][COMPONENT_PROPERTY_NAME].__disconnect__(component, componentPort)
		super().remove_node(n)

	def add_nodes_from(self, nodes_for_adding, components, **attr):
		for (node_from_adding, component) in zip(nodes_for_adding, components):
			self.add_node(node_from_adding, component)

	def remove_nodes_from(self, nodes):
		for node in nodes:
			self.remove_node(node)

	def add_edge(self, u_of_edge, u_of_edge_component_port, v_of_edge, v_of_edge_component_port, **attr):
		self.__updated__ = True
		self.nodes[u_of_edge][COMPONENT_PROPERTY_NAME].__connect__(u_of_edge_component_port, self.nodes[v_of_edge][COMPONENT_PROPERTY_NAME], v_of_edge_component_port)
		super().add_edge(u_of_edge, v_of_edge, **attr)
		self.edges[u_of_edge, v_of_edge][PORT_CONNECTION_PROPERTY_NAME] = (u_of_edge, u_of_edge_component_port, v_of_edge_component_port) # TODO: Maybe delete

	def remove_edge(self, u, v):
		u[COMPONENT_PROPERTY_NAME].__disconnect__(v, self.edges[u, v][PORT_CONNECTION_PROPERTY_NAME][2])
		super().remove_edge(u, v)
	
	def add_edges_from(self, ebunch_to_add, **attr):
		for (u_of_edge, u_of_edge_component_port, v_of_edge, v_of_edge_component_port, *edge_attr) in ebunch_to_add:
			self.add_edge(u_of_edge, u_of_edge_component_port, v_of_edge, v_of_edge_component_port, edge_attr)
	
	def remove_edges_from(self, ebunch):
		for (u, v) in ebunch:
			self.remove_edge(u, v)

	def add_weighted_edges_from(self, ebunch_to_add, weight="weight", **attr):
		raise NotImplementedError('Connections in circuit cannot be weighted')

	@property
	def FreePorts(self) -> list[int, int]:
		if self.__updated__:
			result = list()
			for n in self.nodes:
				for port in range(1, self.nodes[n][COMPONENT_PROPERTY_NAME].PortsNumber + 1):
					if len(self.nodes[n][COMPONENT_PROPERTY_NAME].PortsConnections[port]) < 1:
						result.append((n, port))
			return result
		else:
			self.__updated__ = False
			return self.__freePorts__

	def ResultFrequencies(self) -> list[float]:
		frequenciesTables = [self.Components[name].SMatrices[FREQUENCY_HEADER].unique() for name in self.Components]
		firstFrequenciesTable = frequenciesTables.pop()
		result = list()
		for frequency in firstFrequenciesTable:
			if any([any(frequenciesTable == frequency) for frequenciesTable in frequenciesTables]):
				result.append(frequency)
		return result
	
	def Synthesize(self):
		if len([circuit for circuit in connected_components(self)]) > 1:
			raise Exception('Cannot synthesize one component from several non-connected circuits')

		resultPortsNumber = sum([self.Components[n].PortsNumber for n in self.nodes]) - 2 * len(self.edges)
		result = Component(resultPortsNumber)
		result.SMatrices[FREQUENCY_HEADER] = self.ResultFrequencies()

		resultPorts = dict(enumerate(self.FreePorts))
		# Compute the resulting port regarding existing port on indidual component
		def commonPort(node, port):
			return list(resultPorts.keys())[list(resultPorts.values()).index((node, port))] + 1
		
		# Browse for in-ports
		for (inNode, inPort) in self.FreePorts:
			# Direct copy of S-parameter for input reflection
			commonInPort = commonPort(inNode, inPort)
			
			# Browse for out-ports
			for (outNode, outPort) in [(outNode, outPort) for (outNode, outPort) in self.FreePorts if outNode is not inNode]:
				commonOutPort = commonPort(outNode, outPort)
				orderedNodes = shortest_path(self, inNode, outNode)
				maxNodeIndex = len(orderedNodes)

				for nodeIndex in range(0, maxNodeIndex):
					currentNode = orderedNodes[nodeIndex]
					if nodeIndex == 0:
						nodeInPort = inPort
					else:
						previousNode = orderedNodes[nodeIndex-1]
						connectingEdge = self.edges[currentNode, previousNode]
						inEdge = connectingEdge[PORT_CONNECTION_PROPERTY_NAME]
						nodeInPort = inEdge[1 if inEdge[0] == currentNode else 2]

					if nodeIndex == maxNodeIndex-1:
						nodeOutPort = outPort
					else:
						outEdge = self.edges[orderedNodes[nodeIndex], orderedNodes[nodeIndex+1]][PORT_CONNECTION_PROPERTY_NAME]
						nodeOutPort = outEdge[1 if outEdge[0] == orderedNodes[nodeIndex] else 2]

					newPortName = "S{0}{1} (dB)".format(commonOutPort, commonInPort)

					# To-be-added component with only transmitting ports
					nodeTransmitingSParameters = self.Components[currentNode].SMatrices.filter(regex="^(?!S(?!{0}{1})\d{{2}} \(dB\)).*$".format(nodeOutPort, nodeInPort))
					# Rename transmiting port to correspond to resulting ports
					nodeTransmitingSParameters = nodeTransmitingSParameters.rename(columns={"S{0}{1} (dB)".format(nodeOutPort, nodeInPort): newPortName})

					# Get synthesized component and to-be-added component dependencies
					resultDependencies = result.Dependancies
					nodeTransmitingDependencies = Component.GET_DEPENDENCIES(nodeTransmitingSParameters)

					for newDependency in list(set(nodeTransmitingDependencies) - set(resultDependencies)):
						dependencyIndices = set(nodeTransmitingSParameters[newDependency].dropna())

						# Fill the first serie with the first dependency index
						result.SMatrices[newDependency] = dependencyIndices.pop()

						# Copy the matrix to apply dependencies
						mockupMatrix = result.SMatrices.copy()

						for dependencyIndex in dependencyIndices:
							mockupMatrix[newDependency] = dependencyIndex
							result.SMatrices = concat([result.SMatrices, mockupMatrix])
					
					# Reset results index as it is nor ordered anymore because of new dependencies creation and it will be needed in the next index browsing
					result.SMatrices.reset_index(drop=True, inplace=True)

					columnsToCompare = result.SMatrices.filter(regex="^(?!(?:S\d{2} \(dB\))).*$").columns

					# Browse newly created dependency to add node S-parameters
					for index in result.SMatrices.index:
						nodeClosestResult = nodeTransmitingSParameters
						for columnName in columnsToCompare:
							if columnName in nodeClosestResult:
								nodeClosestResult = nodeClosestResult.loc[nodeClosestResult[columnName] == result.SMatrices.loc[index, columnName]]
						currentValue = float(result.SMatrices.iloc[index][newPortName])
						toAddValue = nodeClosestResult[newPortName].values[0]

						if not isnan(toAddValue):
							if not isnan(currentValue):
								result.SMatrices.loc[index, newPortName] = currentValue + toAddValue
							else:
								result.SMatrices.loc[index, newPortName] = toAddValue

		# Compute maximum power allowed for the synthetized component
		# Max. input power equals the previous synthetized component max. input power, or the current component max. input minus gain of the previous synthetized component
		# result.MaxPowers[commonInPort - 1] = min([result.MaxPowers[commonInPort - 1], self.Components[orderedNodes[nodeIndex]].MaxPowers[commonInPort - 1] - result.SMatrices[power][frequency][commonOutPort - 1, commonInPort - 1]])
						
		return result