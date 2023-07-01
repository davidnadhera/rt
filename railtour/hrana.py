class Hrana():
    def __init__(self, edge):
        self.id = edge.id
        self.point_from_id = edge.point_from_id
        self.point_to_id = edge.point_to_id
        self.departure = edge.departure
        self.arrival = edge.arrival
        self.next_day = edge.next_day
        self.final_transfer = edge.final_transfer
        self.km = edge.km
        self.connections = [x.id for x in edge.connections.all()]
        self.points = edge.point_to.points
        self.region = edge.point_to.region
        self.timeline = edge.point_to.timeline
        self.bonus1 = edge.point_to.bonus1
        self.bonus2 = edge.point_to.bonus2
        self.conn_time = edge.point_to.conn_time

    def __lt__(self, other):
        return self.departure<other.departure

    def count_profit(self):
        self.profit = self.points/(self.arrival-self.departure).total_seconds()*3600.0