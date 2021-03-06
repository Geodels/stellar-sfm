import gc
import sys
import glob
import h5py
import numpy as np
from scipy import spatial
import ruamel.yaml as yaml
from pyevtk.hl import gridToVTK
from scipy.ndimage import gaussian_filter


class stratal:
    def __init__(self, path=None, filename=None, layer=None, model="spherical"):

        self.path = path
        if path is not None:
            filename = self.path + filename

        # Check input file exists
        try:
            with open(filename) as finput:
                pass
        except IOError:
            print("Unable to open file: ", filename)
            raise IOError("The input file is not found...")

        # Open YAML file
        with open(filename, "r") as finput:
            self.input = yaml.load(finput, Loader=yaml.Loader)

        self.radius = 6378137.0
        self._inputParser()

        self.nbCPUs = len(glob.glob1(self.outputDir + "/h5/", "topology.p*"))

        if layer is not None:
            self.layNb = layer
        else:
            self.layNb = int((self.tEnd - self.tStart) / self.strat) + 1

        print("Created sedimentary layers:", self.layNb)

        self.nbfile = len(glob.glob1(self.outputDir + "/h5/", "stratal.*.p0.h5"))

        self.utm = False
        if model != "spherical":
            self.utm = True

        return

    def _inputParser(self):

        try:
            timeDict = self.input["time"]
        except KeyError:
            print("Key 'time' is required and is missing in the input file!")
            raise KeyError("Key time is required in the input file!")

        try:
            self.tStart = timeDict["start"]
        except KeyError:
            print("Key 'start' is required and is missing in the 'time' declaration!")
            raise KeyError("Simulation start time needs to be declared.")

        try:
            self.tEnd = timeDict["end"]
        except KeyError:
            print("Key 'end' is required and is missing in the 'time' declaration!")
            raise KeyError("Simulation end time needs to be declared.")

        try:
            self.strat = timeDict["strat"]
        except KeyError:
            print(
                "Key 'strat' is required to build the stratigraphy in the input file!"
            )
            raise KeyError("Simulation stratal time needs to be declared.")

        try:
            domainDict = self.input["domain"]

            try:
                self.strataFile = domainDict["npstrata"]
            except KeyError:
                self.strataFile = None
        except KeyError:
            self.strataFile = None

        self.multilith = False
        if self.strataFile is not None:
            self.multilith = True

        try:
            outDict = self.input["output"]
            try:
                self.outputDir = outDict["dir"]
            except KeyError:
                self.outputDir = "output"
        except KeyError:
            self.outputDir = "output"

        if self.path is not None:
            self.outputDir = self.path + self.outputDir

        return

    def _xyz2lonlat(self):

        r = np.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)
        # h = r - self.radius

        xs = np.array(self.x)
        ys = np.array(self.y)
        zs = np.array(self.z / r)

        lons = np.arctan2(ys, xs)
        lats = np.arcsin(zs)

        # Convert spherical mesh longitudes and latitudes to degrees
        self.lonlat = np.empty((len(self.x), 2))
        if lons.ndim == 1:
            self.lonlat[:, 0] = np.mod(np.degrees(lons) + 180.0, 360.0)
            self.lonlat[:, 1] = np.mod(np.degrees(lats) + 90, 180.0)
        else:
            self.lonlat[:, 0] = np.mod(np.degrees(lons[:, 0]) + 180.0, 360.0)
            self.lonlat[:, 1] = np.mod(np.degrees(lats[:, 0]) + 90, 180.0)

        self.tree = spatial.cKDTree(self.lonlat, leafsize=10)

        return

    def _lonlat2xyz(self, lon, lat, elev):
        """
        Convert lon / lat (radians) for the spherical triangulation into x,y,z
        on the unit sphere
        """

        xs = np.cos(lat) * np.cos(lon) * self.radius
        ys = np.cos(lat) * np.sin(lon) * self.radius
        zs = np.sin(lat) * self.radius + elev

        return xs, ys, zs

    def _getCoordinates(self):

        for k in range(self.nbCPUs):
            df = h5py.File("%s/h5/topology.p%s.h5" % (self.outputDir, k), "r")
            coords = np.array((df["/coords"]))
            if k == 0:
                self.x, self.y, self.z = np.hsplit(coords, 3)
            else:
                self.x = np.append(self.x, coords[:, 0])
                self.y = np.append(self.y, coords[:, 1])
                self.z = np.append(self.z, coords[:, 2])
            df.close()

        del coords
        self.nbPts = len(self.x)
        if not self.utm:
            self._xyz2lonlat()
        else:
            self.lonlat = np.empty((len(self.x), 2))
            self.lonlat[:, 0] = self.x
            self.lonlat[:, 1] = self.y
            self.tree = spatial.cKDTree(self.lonlat, leafsize=10)

        gc.collect()

        return

    def _getData(self, nbfile):

        for k in range(self.nbCPUs):
            sf = h5py.File("%s/h5/stratal.%s.p%s.h5" % (self.outputDir, nbfile, k), "r")
            if k == 0:
                elev = np.array(sf["/stratZ"])
                th = np.array(sf["/stratH"])
                phiS = np.array(sf["/phiS"])
                if self.multilith:
                    fine = np.array(sf["/stratF"])
                    wth = np.array(sf["/stratW"])
                    phiF = np.array(sf["/phiF"])
                    phiW = np.array(sf["/phiW"])
                # self.sea[layNb] = np.array((sf["/sea"]))
            else:
                elev = np.append(elev, sf["/stratZ"], axis=0)
                th = np.append(th, sf["/stratH"], axis=0)
                phiS = np.append(phiS, sf["/phiS"], axis=0)
                if self.multilith:
                    fine = np.append(fine, sf["/stratF"], axis=0)
                    wth = np.append(wth, sf["/stratW"], axis=0)
                    phiF = np.append(phiF, sf["/phiF"], axis=0)
                    phiW = np.append(phiW, sf["/phiW"], axis=0)
            sf.close()
        self.curLay = th.shape[1]
        print("Total number of sedimentary layers:", self.curLay)

        self.elev = elev
        self.th = th
        self.phiS = phiS
        if self.multilith:
            self.fine = fine
            self.wth = wth
            self.coarse = 1.0 - fine - wth
            self.coarse[self.coarse > 1.0] = 1.0
            self.coarse[self.coarse < 0.0] = 0.0
            self.phiF = phiF
            self.phiW = phiW
            nodepID = np.where(th == 0)
            self.coarse[nodepID] = 0.0
            self.fine[nodepID] = 0.0
            self.wth[nodepID] = 0.0

        return

    def readStratalData(self, fileNb=None):

        if fileNb is None:
            fileNb = self.nbfile - 1

        self._getCoordinates()
        # self.sea = np.empty(self.layNb-1)
        # self.elev = np.empty((self.nbPts, layNb-1))
        # self.erodep = np.empty((self.nbPts, layNb-1))

        # Find associated file:
        self._getData(fileNb)

        return

    def _test_progress(self, job_title, progress):

        length = 20
        block = int(round(length * progress))
        msg = "\r{0}: [{1}] {2}%".format(
            job_title, "#" * block + "-" * (length - block), round(progress * 100, 2)
        )
        if progress >= 1:
            msg += " DONE\r\n"
        sys.stdout.write(msg)
        sys.stdout.flush()

    def buildLonLatMesh(self, res=0.1, nghb=3):

        self.nx = int(360.0 / res)
        self.ny = int(180.0 / res)
        self.lon = np.linspace(0.0, 360.0, self.nx)
        self.lat = np.linspace(0, 180, self.ny)

        self.lon, self.lat = np.meshgrid(self.lon, self.lat)
        xyi = np.dstack([self.lon.flatten(), self.lat.flatten()])[0]
        self.zi = np.empty((self.curLay, self.ny, self.nx))
        self.thi = np.empty((self.curLay, self.ny, self.nx))
        self.phiSi = np.empty((self.curLay, self.ny, self.nx))
        if self.multilith:
            self.finei = np.empty((self.curLay, self.ny, self.nx))
            self.coarsei = np.empty((self.curLay, self.ny, self.nx))
            self.wthi = np.empty((self.curLay, self.ny, self.nx))
            self.phiFi = np.empty((self.curLay, self.ny, self.nx))
            self.phiWi = np.empty((self.curLay, self.ny, self.nx))

        distances, indices = self.tree.query(xyi, k=nghb)
        weights = 1.0 / distances ** 2
        denum = 1.0 / np.sum(weights, axis=1)
        onIDs = np.where(distances[:, 0] == 0)[0]

        print("Start building regular stratigraphic arrays")

        for k in range(self.curLay):

            zz = self.elev[:, k]
            th = self.th[:, k]
            phiS = self.phiS[:, k]
            if self.multilith:
                wth = self.wth[:, k]
                coarse = self.coarse[:, k]
                fine = self.fine[:, k]
                phiF = self.phiF[:, k]
                phiW = self.phiW[:, k]
            self._test_progress("Percentage of arrays built ", (k + 1) / self.curLay)
            zi = np.sum(weights * zz[indices], axis=1) * denum
            thi = np.sum(weights * th[indices], axis=1) * denum
            phiSi = np.sum(weights * phiS[indices], axis=1) * denum
            if self.multilith:
                wthi = np.sum(weights * wth[indices], axis=1) * denum
                # coarsei = np.sum(weights * coarse[indices], axis=1) * denum
                finei = np.sum(weights * fine[indices], axis=1) * denum
                phiFi = np.sum(weights * phiF[indices], axis=1) * denum
                phiWi = np.sum(weights * phiW[indices], axis=1) * denum
                coarsei = 1.0 - finei - wthi
                nocoarseID = np.where(np.sum(coarse[indices], axis=1) == 0.0)[0]
                coarsei[nocoarseID] = 0.0

            if len(onIDs) > 0:
                zi[onIDs] = zz[indices[onIDs, 0]]
                thi[onIDs] = th[indices[onIDs, 0]]
                phiSi[onIDs] = phiS[indices[onIDs, 0]]
                if self.multilith:
                    finei[onIDs] = fine[indices[onIDs, 0]]
                    wthi[onIDs] = wth[indices[onIDs, 0]]
                    phiWi[onIDs] = phiW[indices[onIDs, 0]]
                    coarsei[onIDs] = 1.0 - finei[onIDs] - wthi[onIDs]

            if self.multilith:
                totperc = finei + coarsei + wthi
                finei = np.divide(
                    finei, totperc, out=np.zeros_like(finei), where=totperc != 0
                )
                wthi = np.divide(
                    wthi, totperc, out=np.zeros_like(wthi), where=totperc != 0
                )
                coarsei = np.divide(
                    coarsei, totperc, out=np.zeros_like(coarsei), where=totperc != 0
                )

            nodepID = np.where(thi == 0)[0]
            if len(nodepID) > 0:
                if self.multilith:
                    coarsei[nodepID] = 0.0
                    finei[nodepID] = 0.0
                    wthi[nodepID] = 0.0

            self.zi[k, :, :] = np.reshape(zi, (self.ny, self.nx))
            self.thi[k, :, :] = np.reshape(thi, (self.ny, self.nx))
            self.phiSi[k, :, :] = np.reshape(phiSi, (self.ny, self.nx))
            if k > 0:
                id1, id2 = np.where(self.phiSi[k, :, :,] < self.phiSi[k - 1, :, :])
                if len(id1) > 0:
                    self.phiSi[k, id1, id2] = self.phiSi[k - 1, id1, id2]

            if self.multilith:
                self.wthi[k, :, :] = np.reshape(wthi, (self.ny, self.nx))
                self.coarsei[k, :, :] = np.reshape(coarsei, (self.ny, self.nx))
                self.finei[k, :, :] = np.reshape(finei, (self.ny, self.nx))
                self.phiFi[k, :, :] = np.reshape(phiFi, (self.ny, self.nx))
                self.phiWi[k, :, :] = np.reshape(phiWi, (self.ny, self.nx))
                if k > 0:
                    id1, id2 = np.where(self.phiFi[k, :, :,] < self.phiFi[k - 1, :, :])
                    if len(id1) > 0:
                        self.phiFi[k, id1, id2] = self.phiFi[k - 1, id1, id2]
                    id1, id2 = np.where(self.phiWi[k, :, :,] < self.phiWi[k - 1, :, :])
                    if len(id1) > 0:
                        self.phiWi[k, id1, id2] = self.phiWi[k - 1, id1, id2]

        del weights, denum, onIDs, zz, zi, th, xyi, thi, phiSi
        if self.multilith:
            del wthi, finei, coarsei, phiFi, phiWi
        gc.collect()

        return

    def buildUTMmesh(self, res=5000.0, nghb=3):

        xo = self.x.min()
        xm = self.x.max()
        yo = self.y.min()
        ym = self.y.max()

        self.lon = np.arange(xo, xm + res, res)
        self.lat = np.arange(yo, ym + res, res)
        self.nx = len(self.lon)
        self.ny = len(self.lat)

        self.lon, self.lat = np.meshgrid(self.lon, self.lat)
        xyi = np.dstack([self.lon.flatten(), self.lat.flatten()])[0]
        self.zi = np.empty((self.curLay, self.ny, self.nx))
        self.thi = np.empty((self.curLay, self.ny, self.nx))
        self.phiSi = np.empty((self.curLay, self.ny, self.nx))
        if self.multilith:
            self.finei = np.empty((self.curLay, self.ny, self.nx))
            self.coarsei = np.empty((self.curLay, self.ny, self.nx))
            self.wthi = np.empty((self.curLay, self.ny, self.nx))
            self.phiFi = np.empty((self.curLay, self.ny, self.nx))
            self.phiWi = np.empty((self.curLay, self.ny, self.nx))

        distances, indices = self.tree.query(xyi, k=nghb)
        weights = 1.0 / (distances + 0.000001) ** 2
        denum = 1.0 / np.sum(weights, axis=1)
        onIDs = np.where(distances[:, 0] < 0.000001)[0]

        print("Start building regular stratigraphic arrays")

        for k in range(self.curLay):

            zz = self.elev[:, k]
            th = self.th[:, k]
            phiS = self.phiS[:, k]
            if self.multilith:
                wth = self.wth[:, k]
                coarse = self.coarse[:, k]
                fine = self.fine[:, k]
                phiF = self.phiF[:, k]
                phiW = self.phiW[:, k]
            self._test_progress("Percentage of arrays built ", (k + 1) / self.curLay)
            zi = np.sum(weights * zz[indices], axis=1) * denum
            thi = np.sum(weights * th[indices], axis=1) * denum
            phiSi = np.sum(weights * phiS[indices], axis=1) * denum
            if self.multilith:
                wthi = np.sum(weights * wth[indices], axis=1) * denum
                # coarsei = np.sum(weights * coarse[indices], axis=1) * denum
                finei = np.sum(weights * fine[indices], axis=1) * denum
                phiFi = np.sum(weights * phiF[indices], axis=1) * denum
                phiWi = np.sum(weights * phiW[indices], axis=1) * denum
                coarsei = 1.0 - finei - wthi
                nocoarseID = np.where(np.sum(coarse[indices], axis=1) == 0.0)[0]
                coarsei[nocoarseID] = 0.0

            if len(onIDs) > 0:
                zi[onIDs] = zz[indices[onIDs, 0]]
                thi[onIDs] = th[indices[onIDs, 0]]
                phiSi[onIDs] = phiS[indices[onIDs, 0]]
                if self.multilith:
                    finei[onIDs] = fine[indices[onIDs, 0]]
                    wthi[onIDs] = wth[indices[onIDs, 0]]
                    phiWi[onIDs] = phiW[indices[onIDs, 0]]
                    coarsei[onIDs] = 1.0 - finei[onIDs] - wthi[onIDs]

            if self.multilith:
                totperc = finei + coarsei + wthi
                finei = np.divide(
                    finei, totperc, out=np.zeros_like(finei), where=totperc != 0
                )
                wthi = np.divide(
                    wthi, totperc, out=np.zeros_like(wthi), where=totperc != 0
                )
                coarsei = np.divide(
                    coarsei, totperc, out=np.zeros_like(coarsei), where=totperc != 0
                )

            nodepID = np.where(thi == 0)[0]
            if len(nodepID) > 0:
                if self.multilith:
                    coarsei[nodepID] = 0.0
                    finei[nodepID] = 0.0
                    wthi[nodepID] = 0.0

            self.zi[k, :, :] = np.reshape(zi, (self.ny, self.nx))
            self.thi[k, :, :] = np.reshape(thi, (self.ny, self.nx))
            self.phiSi[k, :, :] = np.reshape(phiSi, (self.ny, self.nx))
            if k > 0:
                id1, id2 = np.where(self.phiSi[k, :, :,] < self.phiSi[k - 1, :, :])
                if len(id1) > 0:
                    self.phiSi[k, id1, id2] = self.phiSi[k - 1, id1, id2]

            if self.multilith:
                self.wthi[k, :, :] = np.reshape(wthi, (self.ny, self.nx))
                self.coarsei[k, :, :] = np.reshape(coarsei, (self.ny, self.nx))
                self.finei[k, :, :] = np.reshape(finei, (self.ny, self.nx))
                self.phiFi[k, :, :] = np.reshape(phiFi, (self.ny, self.nx))
                self.phiWi[k, :, :] = np.reshape(phiWi, (self.ny, self.nx))
                if k > 0:
                    id1, id2 = np.where(self.phiFi[k, :, :,] < self.phiFi[k - 1, :, :])
                    if len(id1) > 0:
                        self.phiFi[k, id1, id2] = self.phiFi[k - 1, id1, id2]
                    id1, id2 = np.where(self.phiWi[k, :, :,] < self.phiWi[k - 1, :, :])
                    if len(id1) > 0:
                        self.phiWi[k, id1, id2] = self.phiWi[k - 1, id1, id2]

        del weights, denum, onIDs, zz, zi, th, xyi, thi, phiSi
        if self.multilith:
            del wthi, finei, coarsei, phiFi, phiWi
        gc.collect()

        return

    def writeMesh(self, vtkfile="mesh", lons=None, lats=None, sigma=0.0):
        """
        Create a vtk unstructured grid based on current time step stratal parameters.
        """

        if not self.utm:
            lon = np.linspace(0.0, 360.0, self.nx)
            lat = np.linspace(0.0, 180.0, self.ny)

            if lons is None:
                lons = [lon[0], lon[-1]]
            else:
                lons[0] = np.where(self.lon[0, :] >= lons[0] + 180)[0].min()
                lons[1] = np.where(self.lon[0, :] >= lons[1] + 180)[0].min()
            if lats is None:
                lats = [lat[0], lat[-1]]
            else:
                lats[0] = np.where(self.lat[:, 0] >= lats[0] + 90)[0].min()
                lats[1] = np.where(self.lat[:, 0] >= lats[1] + 90)[0].min()
        else:
            xo = self.x.min()
            xm = self.x.max()
            yo = self.y.min()
            ym = self.y.max()
            lon = np.linspace(xo, xm, self.nx)
            lat = np.linspace(yo, ym, self.ny)
            lons = [0, self.nx]
            lats = [0, self.ny]

        x = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
        y = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
        z = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
        e = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
        h = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
        t = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
        ps = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))

        if self.multilith:
            c = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
            f = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
            w = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
            pf = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))
            pw = np.zeros((lons[1] - lons[0], lats[1] - lats[0], self.curLay))

        zz = self.zi[-1, lats[0] : lats[1], lons[0] : lons[1]]
        zz = gaussian_filter(zz, sigma)

        if not self.utm:
            hscale = 110000.0
        else:
            hscale = 1.0
        xmax = -1.0e12
        ymax = -1.0e12
        for k in range(self.curLay - 1, -1, -1):
            th = gaussian_filter(self.thi[k, :, :], sigma)
            th[th < 0] = 0.0
            if k < self.curLay - 1:
                thu = gaussian_filter(self.thi[k + 1, :, :], sigma)
                thu[thu < 0] = 0.0
            for j in range(lats[1] - lats[0]):
                for i in range(lons[1] - lons[0]):
                    x[i, j, k] = (lon[i + lons[0]] - lon[lons[0]]) * hscale
                    y[i, j, k] = (lat[j + lats[0]] - lat[lats[0]]) * hscale
                    xmax = max(xmax, x[i, j, k])
                    ymax = max(ymax, y[i, j, k])
                    if k == self.curLay - 1:
                        z[i, j, k] = zz[j, i]
                    else:
                        z[i, j, k] = z[i, j, k + 1] - thu[j + lats[0], i + lons[0]]
                    e[i, j, k] = self.zi[k, j + lats[0], i + lons[0]]
                    h[i, j, k] = th[j + lats[0], i + lons[0]]
                    t[i, j, k] = k
                    ps[i, j, k] = self.phiSi[k, j + lats[0], i + lons[0]]
                    if self.multilith:
                        c[i, j, k] = self.coarsei[k, j + lats[0], i + lons[0]]
                        f[i, j, k] = self.finei[k, j + lats[0], i + lons[0]]
                        w[i, j, k] = self.wthi[k, j + lats[0], i + lons[0]]
                        pf[i, j, k] = self.phiFi[k, j + lats[0], i + lons[0]]
                        pw[i, j, k] = self.phiWi[k, j + lats[0], i + lons[0]]

        if self.multilith:
            gridToVTK(
                vtkfile,
                x,
                y,
                z,
                pointData={
                    "dep elev": e,
                    "th": h,
                    "layID": t,
                    "%c": c,
                    "%f": f,
                    "%w": w,
                    "porC": ps,
                    "porF": pf,
                    "porW": pw,
                },
            )
        else:
            gridToVTK(
                vtkfile,
                x,
                y,
                z,
                pointData={"dep elev": e, "th": h, "layID": t, "poro": ps},
            )

        return [xmax, ymax]
