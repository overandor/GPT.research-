// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title KPI Token Factory Suite
/// @notice Deploys and manages a swarm of KPI-linked tokens, prompt appraisal routing,
///         and a composite index backed by on-chain oracle updates.
/// @dev Designed as a single deployable artifact for multi-KPI economies.

// -----------------------------------------------------------------------------
//                               UTILITY LAYERS
// -----------------------------------------------------------------------------

contract Ownable {
    address private _owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        _transferOwnership(msg.sender);
    }

    modifier onlyOwner() {
        require(msg.sender == _owner, "Ownable: caller is not the owner");
        _;
    }

    function owner() public view returns (address) {
        return _owner;
    }

    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Ownable: zero address");
        _transferOwnership(newOwner);
    }

    function _transferOwnership(address newOwner) internal {
        address previousOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(previousOwner, newOwner);
    }
}

abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

// -----------------------------------------------------------------------------
//                                TOKEN CONTRACT
// -----------------------------------------------------------------------------

contract KPIToken is Ownable {
    string public name;
    string public symbol;
    uint8 private immutable _decimals;
    uint256 private _totalSupply;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Approval(address indexed owner, address indexed spender, uint256 amount);

    constructor(string memory name_, string memory symbol_, uint8 decimals_) {
        name = name_;
        symbol = symbol_;
        _decimals = decimals_;
    }

    function decimals() external view returns (uint8) {
        return _decimals;
    }

    function totalSupply() external view returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    function allowance(address holder, address spender) external view returns (uint256) {
        return _allowances[holder][spender];
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= amount, "ERC20: insufficient allowance");
        _transfer(from, to, amount);
        _approve(from, msg.sender, currentAllowance - amount);
        return true;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "ERC20: mint to zero");
        _totalSupply += amount;
        _balances[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function burn(address from, uint256 amount) external onlyOwner {
        uint256 balance = _balances[from];
        require(balance >= amount, "ERC20: burn exceeds balance");
        _balances[from] = balance - amount;
        _totalSupply -= amount;
        emit Transfer(from, address(0), amount);
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), "ERC20: transfer to zero");
        uint256 balance = _balances[from];
        require(balance >= amount, "ERC20: insufficient balance");
        _balances[from] = balance - amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }

    function _approve(address holder, address spender, uint256 amount) internal {
        _allowances[holder][spender] = amount;
        emit Approval(holder, spender, amount);
    }
}

// -----------------------------------------------------------------------------
//                                ORACLE CONTRACT
// -----------------------------------------------------------------------------

contract KPIOracle is Ownable {
    uint256 public lastValue;
    uint256 public lastEpoch;

    event ValueSubmitted(uint256 indexed epoch, uint256 value);

    function submit(uint256 epoch, uint256 value) external onlyOwner {
        require(epoch > lastEpoch, "Oracle: stale epoch");
        lastEpoch = epoch;
        lastValue = value;
        emit ValueSubmitted(epoch, value);
    }
}

// -----------------------------------------------------------------------------
//                             PROMPT NFT REGISTRY
// -----------------------------------------------------------------------------

contract PromptNFT is Ownable {
    string public constant name = "Prompt Appraisal NFT";
    string public constant symbol = "PRMPT";

    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => address) private _tokenApprovals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    function balanceOf(address owner_) public view returns (uint256) {
        require(owner_ != address(0), "ERC721: zero address");
        return _balances[owner_];
    }

    function ownerOf(uint256 tokenId) public view returns (address) {
        address owner_ = _owners[tokenId];
        require(owner_ != address(0), "ERC721: nonexistent token");
        return owner_;
    }

    function exists(uint256 tokenId) external view returns (bool) {
        return _owners[tokenId] != address(0);
    }

    function approve(address to, uint256 tokenId) external {
        address owner_ = ownerOf(tokenId);
        require(to != owner_, "ERC721: approval to owner");
        require(msg.sender == owner_ || isApprovedForAll(owner_, msg.sender), "ERC721: not authorized");
        _tokenApprovals[tokenId] = to;
        emit Approval(owner_, to, tokenId);
    }

    function getApproved(uint256 tokenId) public view returns (address) {
        require(_owners[tokenId] != address(0), "ERC721: nonexistent token");
        return _tokenApprovals[tokenId];
    }

    function setApprovalForAll(address operator, bool approved) external {
        require(operator != msg.sender, "ERC721: approve to caller");
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function isApprovedForAll(address owner_, address operator) public view returns (bool) {
        return _operatorApprovals[owner_][operator];
    }

    function transferFrom(address from, address to, uint256 tokenId) public {
        require(_isApprovedOrOwner(msg.sender, tokenId), "ERC721: not authorized");
        require(ownerOf(tokenId) == from, "ERC721: wrong from");
        require(to != address(0), "ERC721: transfer to zero");
        _transfer(from, to, tokenId);
    }

    function safeTransferFrom(address from, address to, uint256 tokenId) external {
        transferFrom(from, to, tokenId);
        require(_checkOnERC721Received(from, to, tokenId, ""), "ERC721: non ERC721Receiver");
    }

    function safeTransferFrom(address from, address to, uint256 tokenId, bytes memory data) external {
        transferFrom(from, to, tokenId);
        require(_checkOnERC721Received(from, to, tokenId, data), "ERC721: non ERC721Receiver");
    }

    function mint(address to, uint256 tokenId) external onlyOwner {
        require(to != address(0), "ERC721: mint to zero");
        require(_owners[tokenId] == address(0), "ERC721: token exists");
        _owners[tokenId] = to;
        _balances[to] += 1;
        emit Transfer(address(0), to, tokenId);
    }

    function burn(uint256 tokenId) external onlyOwner {
        address owner_ = ownerOf(tokenId);
        delete _tokenApprovals[tokenId];
        _balances[owner_] -= 1;
        delete _owners[tokenId];
        emit Transfer(owner_, address(0), tokenId);
    }

    function _transfer(address from, address to, uint256 tokenId) internal {
        delete _tokenApprovals[tokenId];
        _balances[from] -= 1;
        _balances[to] += 1;
        _owners[tokenId] = to;
        emit Transfer(from, to, tokenId);
    }

    function _isApprovedOrOwner(address spender, uint256 tokenId) internal view returns (bool) {
        address owner_ = ownerOf(tokenId);
        return (spender == owner_ || getApproved(tokenId) == spender || isApprovedForAll(owner_, spender));
    }

    function _checkOnERC721Received(address from, address to, uint256 tokenId, bytes memory data) private returns (bool) {
        if (to.code.length == 0) {
            return true;
        }
        (bool success, bytes memory returndata) = to.call(abi.encodeWithSignature("onERC721Received(address,address,uint256,bytes)", msg.sender, from, tokenId, data));
        if (!success || returndata.length < 32) {
            return false;
        }
        bytes4 selector = abi.decode(returndata, (bytes4));
        return selector == 0x150b7a02;
    }
}

// -----------------------------------------------------------------------------
//                               KPI REGISTRY CORE
// -----------------------------------------------------------------------------

contract KPIRegistry is Ownable {
    struct KPIConfig {
        string name;
        string symbol;
        address token;
        address oracle;
        uint8 decimals;
        uint256 emissionMultiplier;
        uint256 lastValue;
        bool live;
    }

    mapping(bytes32 => KPIConfig) private _kpis;
    bytes32[] private _kpiIds;
    mapping(address => bool) public authorizedMinters;

    address public emissionsCollector;

    event KPIDeployed(bytes32 indexed id, string name, string symbol, address token, address oracle);
    event KPIValueUpdated(bytes32 indexed id, uint256 epoch, uint256 value, uint256 mintedAmount);
    event AuthorizedMinter(address indexed account, bool allowed);
    event EmissionsCollectorUpdated(address indexed collector);

    constructor(address emissionsCollector_) {
        require(emissionsCollector_ != address(0), "Registry: zero collector");
        emissionsCollector = emissionsCollector_;
        _seedKPIs();
    }

    function totalKPIs() external view returns (uint256) {
        return _kpiIds.length;
    }

    function listKPIIds() external view returns (bytes32[] memory ids) {
        ids = new bytes32[](_kpiIds.length);
        for (uint256 i = 0; i < _kpiIds.length; i++) {
            ids[i] = _kpiIds[i];
        }
    }

    function getKPIMetadata(bytes32 id) external view returns (
        string memory name_,
        string memory symbol_,
        address token,
        address oracle,
        uint8 decimals,
        uint256 emissionMultiplier,
        uint256 lastValue,
        bool live
    ) {
        KPIConfig storage cfg = _requireKPI(id);
        return (cfg.name, cfg.symbol, cfg.token, cfg.oracle, cfg.decimals, cfg.emissionMultiplier, cfg.lastValue, cfg.live);
    }

    function getKPIValue(bytes32 id) external view returns (uint256) {
        KPIConfig storage cfg = _requireKPI(id);
        return cfg.lastValue;
    }

    function setAuthorizedMinter(address account, bool allowed) external onlyOwner {
        authorizedMinters[account] = allowed;
        emit AuthorizedMinter(account, allowed);
    }

    function setEmissionsCollector(address collector) external onlyOwner {
        require(collector != address(0), "Registry: zero collector");
        emissionsCollector = collector;
        emit EmissionsCollectorUpdated(collector);
    }

    function updateEmissionMultiplier(bytes32 id, uint256 multiplier) external onlyOwner {
        KPIConfig storage cfg = _requireKPI(id);
        cfg.emissionMultiplier = multiplier;
    }

    function updateKPI(bytes32 id, uint256 epoch, uint256 value) external onlyOwner returns (uint256 mintedAmount) {
        KPIConfig storage cfg = _requireKPI(id);
        KPIOracle oracle = KPIOracle(cfg.oracle);
        oracle.submit(epoch, value);
        mintedAmount = 0;
        if (value > cfg.lastValue) {
            uint256 delta = value - cfg.lastValue;
            mintedAmount = delta * cfg.emissionMultiplier;
            KPIToken(cfg.token).mint(emissionsCollector, mintedAmount);
        }
        cfg.lastValue = value;
        emit KPIValueUpdated(id, epoch, value, mintedAmount);
    }

    function mintForAppraisal(bytes32 id, address to, uint256 amount) external {
        require(authorizedMinters[msg.sender], "Registry: unauthorized minter");
        KPIConfig storage cfg = _requireKPI(id);
        require(cfg.live, "Registry: KPI inactive");
        KPIToken(cfg.token).mint(to, amount);
    }

    function deactivateKPI(bytes32 id) external onlyOwner {
        KPIConfig storage cfg = _requireKPI(id);
        cfg.live = false;
    }

    function reactivateKPI(bytes32 id) external onlyOwner {
        KPIConfig storage cfg = _requireKPI(id);
        cfg.live = true;
    }

    function isRegistered(bytes32 id) external view returns (bool) {
        return _kpis[id].token != address(0);
    }

    function _seedKPIs() internal {
        _registerKPI("Prompt Yield", "PYLD", 18, 1e16);
        _registerKPI("Entropy Profit Density", "EPDX", 18, 1e16);
        _registerKPI("Dormant Reserve Activation", "DRAX", 18, 1e16);
        _registerKPI("Latency-Liquidity Overlap", "LLOX", 18, 1e16);
        _registerKPI("Cognitive Dollar Extraction", "CDLX", 18, 1e16);
        _registerKPI("Ambiguity Leverage Index", "ALIX", 18, 1e16);
        _registerKPI("Social Proof Velocity", "SPVX", 18, 1e16);
        _registerKPI("Dormancy Time Premium", "DTPX", 18, 1e16);
        _registerKPI("Sovereign Credit Entropy", "SCEX", 18, 1e16);
        _registerKPI("Cross-Jurisdictional Entropy Spread", "CJEX", 18, 1e16);
        _registerKPI("Recursive Reuse Yield", "RRYX", 18, 1e16);
        _registerKPI("Liquidity Echo Value", "LEVX", 18, 1e16);
        _registerKPI("Obscurity Extraction Value", "OEVX", 18, 1e16);
        _registerKPI("Prompt Dollar Multiplier", "PDMX", 18, 1e16);
        _registerKPI("Influence Dollar Ratio", "IDRX", 18, 1e16);
        _registerKPI("Settlement Slippage Penalty", "SSPX", 18, 1e16);
        _registerKPI("Trust Residual", "TRUX", 18, 1e16);
        _registerKPI("Quality-Latency Tradeoff", "QLTX", 18, 1e16);
        _registerKPI("Conversion Velocity Ratio", "CVRX", 18, 1e16);
        _registerKPI("Stability Under Perturbation", "STBX", 18, 1e16);
        _registerKPI("Safety Compliance Rate", "SAFE", 18, 1e16);
        _registerKPI("Cost Down Efficiency", "COST", 18, 1e16);
        _registerKPI("Retention Velocity", "RETX", 18, 1e16);
        _registerKPI("Error Budget Utilization", "ERRX", 18, 1e16);
        _registerKPI("Uptime Weighted by Users", "UPTX", 18, 1e16);
        _registerKPI("Performance Quotient", "PRFX", 18, 1e16);
        _registerKPI("Volatility Adjusted Adoption", "VLTX", 18, 1e16);
        _registerKPI("AUC Uplift", "AUCX", 18, 1e16);
        _registerKPI("Human Approval Rate", "HUMX", 18, 1e16);
        _registerKPI("Evidence Density", "EVDX", 18, 1e16);
    }

    function _registerKPI(
        string memory name_,
        string memory symbol_,
        uint8 decimals_,
        uint256 emissionMultiplier_
    ) internal {
        bytes32 id = keccak256(bytes(symbol_));
        require(_kpis[id].token == address(0), "Registry: duplicate symbol");
        KPIToken token = new KPIToken(name_, symbol_, decimals_);
        KPIOracle oracle = new KPIOracle();
        KPIConfig storage cfg = _kpis[id];
        cfg.name = name_;
        cfg.symbol = symbol_;
        cfg.token = address(token);
        cfg.oracle = address(oracle);
        cfg.decimals = decimals_;
        cfg.emissionMultiplier = emissionMultiplier_;
        cfg.lastValue = 0;
        cfg.live = true;
        _kpiIds.push(id);
        emit KPIDeployed(id, name_, symbol_, address(token), address(oracle));
    }

    function _requireKPI(bytes32 id) internal view returns (KPIConfig storage) {
        KPIConfig storage cfg = _kpis[id];
        require(cfg.token != address(0), "Registry: unknown KPI");
        return cfg;
    }
}

// -----------------------------------------------------------------------------
//                           APPRAISAL ROUTER & REWARDS
// -----------------------------------------------------------------------------

contract AppraisalRouter is Ownable, ReentrancyGuard {
    KPIRegistry public immutable registry;
    PromptNFT public immutable promptNFT;
    uint256 public immutable baseUnit;
    uint16 public constant MAX_BASIS = 10_000;

    mapping(address => bool) public appraisers;

    event AppraiserUpdated(address indexed appraiser, bool allowed);
    event AppraisalRecorded(uint256 indexed promptId, address indexed recipient, bytes32 indexed kpiId, uint16 weight, uint256 reward);

    constructor(KPIRegistry registry_, PromptNFT promptNFT_, uint256 baseUnit_) {
        require(address(registry_) != address(0), "Router: zero registry");
        require(address(promptNFT_) != address(0), "Router: zero nft");
        require(baseUnit_ > 0, "Router: zero base");
        registry = registry_;
        promptNFT = promptNFT_;
        baseUnit = baseUnit_;
    }

    modifier onlyAppraiser() {
        require(appraisers[msg.sender], "Router: not appraiser");
        _;
    }

    function setAppraiser(address account, bool allowed) external onlyOwner {
        appraisers[account] = allowed;
        emit AppraiserUpdated(account, allowed);
    }

    function appraise(
        address recipient,
        uint256 promptId,
        bytes32[] calldata kpiIds,
        uint16[] calldata weights
    ) external nonReentrant onlyAppraiser {
        require(recipient != address(0), "Router: zero recipient");
        require(kpiIds.length == weights.length && kpiIds.length > 0, "Router: invalid input");
        uint256 totalBasis = 0;
        for (uint256 i = 0; i < weights.length; i++) {
            totalBasis += weights[i];
        }
        require(totalBasis <= MAX_BASIS, "Router: overweight");

        if (!promptNFT.exists(promptId)) {
            promptNFT.mint(recipient, promptId);
        }

        for (uint256 i = 0; i < kpiIds.length; i++) {
            uint256 reward = (baseUnit * weights[i]) / MAX_BASIS;
            if (reward == 0) {
                continue;
            }
            registry.mintForAppraisal(kpiIds[i], recipient, reward);
            emit AppraisalRecorded(promptId, recipient, kpiIds[i], weights[i], reward);
        }
    }
}

// -----------------------------------------------------------------------------
//                                COMPOSITE INDEX
// -----------------------------------------------------------------------------

contract CompositeIndex is Ownable {
    KPIRegistry public immutable registry;
    bytes32[] private _components;
    mapping(bytes32 => uint32) public weights; // scaled by 1e6
    uint32 public constant WEIGHT_SCALE = 1_000_000;

    event IndexWeightsUpdated(bytes32[] ids, uint32[] weights);

    constructor(KPIRegistry registry_) {
        require(address(registry_) != address(0), "Index: zero registry");
        registry = registry_;
    }

    function components() external view returns (bytes32[] memory) {
        bytes32[] memory ids = new bytes32[](_components.length);
        for (uint256 i = 0; i < _components.length; i++) {
            ids[i] = _components[i];
        }
        return ids;
    }

    function setWeights(bytes32[] calldata ids, uint32[] calldata newWeights) external onlyOwner {
        require(ids.length == newWeights.length && ids.length > 0, "Index: invalid input");
        uint256 total;
        for (uint256 i = 0; i < ids.length; i++) {
            total += newWeights[i];
        }
        require(total == WEIGHT_SCALE, "Index: weights must sum to scale");
        for (uint256 i = 0; i < _components.length; i++) {
            weights[_components[i]] = 0;
        }
        delete _components;
        for (uint256 i = 0; i < ids.length; i++) {
            weights[ids[i]] = newWeights[i];
            _components.push(ids[i]);
        }
        emit IndexWeightsUpdated(ids, newWeights);
    }

    function indexValue() external view returns (uint256 value) {
        for (uint256 i = 0; i < _components.length; i++) {
            bytes32 id = _components[i];
            uint256 oracleValue = registry.getKPIValue(id);
            value += (oracleValue * weights[id]) / WEIGHT_SCALE;
        }
    }
}

// -----------------------------------------------------------------------------
//                                 DEPLOY GUIDE
// -----------------------------------------------------------------------------
// 1. Deploy KPIRegistry with the treasury/emissions collector address.
// 2. Deploy PromptNFT.
// 3. Deploy AppraisalRouter with registry, nft, and base reward (e.g., 1e18).
// 4. Transfer PromptNFT ownership to the router.
// 5. Authorize the router inside KPIRegistry via setAuthorizedMinter.
// 6. Set appraisers on the router. Submit oracle updates via KPIRegistry.updateKPI.
// 7. Deploy CompositeIndex to track a weighted basket of KPI oracle values.
// -----------------------------------------------------------------------------
