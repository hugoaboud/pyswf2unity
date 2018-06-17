from numpy import matrix, asscalar, arctan2, pi
from numpy.linalg import norm
from config import SCALE

##
#   Transformation Matrix
##

# |a,c,e|
# |b,d,f| <=> [a,b,c,d,e,f]
# |0,0,1|      0 1 2 3 4 5
#
# 3matrix         matrix

class TMatrix(object):
    def __init__(self):
        self.matrix = [1,0,0,1,0,0]
    def __init__(self, matrix):
        self.matrix = matrix
    def getPosition(self):
        if (self.matrix == None): return None
        return [self.matrix[4]*SCALE,self.matrix[5]*SCALE]
    def getScale(self):
        if (self.matrix == None): return None
        return [asscalar(norm([self.matrix[0],self.matrix[1]])),asscalar(norm([self.matrix[2],self.matrix[3]]))]
    def getEuler(self):
        if (self.matrix == None): return None
        euler = asscalar(arctan2(self.matrix[0],self.matrix[1])*180/pi-90)
        return euler;
    def __mul__(self, other):
        if not other is TMatrix: other = TMatrix(other)
        matrix_a = matrix([[self.matrix[0],self.matrix[2],self.matrix[4]],[self.matrix[1],self.matrix[3],self.matrix[5]],[0,0,1]])
        matrix_b = matrix([[other.matrix[0],other.matrix[2],other.matrix[4]],[other.matrix[1],other.matrix[3],other.matrix[5]],[0,0,1]])
        mult = (matrix_a * matrix_b).tolist()
        return TMatrix([mult[0][0],mult[1][0],mult[0][1],mult[1][1],mult[0][2],mult[1][2]])
    def __rmul__(self,other):
        if not other is TMatrix: return
        return __mul__(other, self)

##
#   Animation Type
##

class AnimType:
    POSITION = 0
    SCALE = 1
    EULER = 2
    ISACTIVE = 3

    @staticmethod
    def Name(type):
        return {
            -1:"Invalid",
            0:"Position",
            1:"Scale",
            2:"Euler",
            3:"IsActive"
        }.get(type, -1);
